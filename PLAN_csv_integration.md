# Plan: Use real EmotiBit CSV (`2026-04-25_11-32-15-268408.csv`) to drive the Daily Review

## Goal

Replace the static `review_data.js` mock with data parsed live from the real EmotiBit CSV. The Day Recap timeline, meters, scrubber, and dashboards must reflect what actually happened during the recording session (`2026-04-25` starting `11:32:15`, ~3.6 hours, 25,011 HR samples).

The biofeedback challenge (`biosignal.js`) is **out of scope** — leave it untouched. It already supports live WebSocket + mock mode.

## CSV format (EmotiBit) — quick reference

Each row: `LocalTimestamp,PacketNumber,DataLength,TypeTag,ProtocolVersion,DataReliability,Value0[,Value1,...]`

- Column 1 (`LocalTimestamp`): ms since device boot. Treat the **first** row's value as `t0`. All subsequent timestamps are `(ts - t0)` ms after `11:32:15`.
- Column 4 (`TypeTag`): the signal type. The ones we use:
  - `HR`  — heart rate in bpm (sparse, ~1 Hz, 25,011 rows)
  - `SF`  — skin response frequency (EDA proxy, ~3 Hz)
  - `T1`  — skin temperature °C
  - `AX`/`AY`/`AZ` — accelerometer (g) for activity
- Columns 7+: one or more numeric samples (DataLength tells you how many)

We ignore `RB`, `EM`, `RD`, `AK`, `B%`, `BI`, `BV`, `MX`/`MY`/`MZ`, `GX`/`GY`/`GZ`, `EA`, `EL`, `PI`, `PR`, `PG`, `TH`, `TL`, `SA`, `SR` for this task.

Recording window: file name encodes start = `2026-04-25 11:32:15`. Last timestamp `32581238` minus first `2119215` ≈ **30,462,023 ms ≈ 8.46 hours** of clock time covered (with gaps). End ≈ `19:59`.

## Target data shape

The renderer (`renderDashboards`, `renderQuestions`, `dayRecap` module) expects the same object shape as `reviewDataObj` in `review_data.js`. Match it exactly so we don't have to touch the renderers. Required keys:

```
{
  date, user_id,
  summary: { cardio_avg, cardio_vs_baseline_pct, cardio_peak_historical, cardio_peak_date,
             stress_avg, stress_vs_baseline_pct, stress_peak_historical, stress_peak_date,
             dominant_state, tagline },
  dashboards: {
    cardio: { label, unit, curve:[{t,v},...], baseline_line, highlights:[{metric,id,start,end,peak,pct_above_mean,duration_min,start_idx}], gauge:{value,fill_pct,delta_pct} },
    stress: { ...same shape... }
  },
  questions: [ { id, category, text, linked_highlight, guess?:{activity,confidence} }, ... ]
}
```

The Day Recap also reads two module-private constants in `ui_mockup.html`:
- `REPORTS` (~line 2355): array of `{ t, state, text, question, mockAnswer }` per 30-min slot
- `METERS` (~line 2380): array of `{ id, title, value, ringPct, color, evalText, vsWeek }`

Both must be populated from the parsed CSV.

## Files to change

1. **`ui_mockup.html`** — most edits land here.
2. **New file `csv_parser.js`** — pure parser, no DOM.
3. Leave `review_data.js`, `biosignal.js`, `tips.js` untouched (`review_data.js` stays as a fallback only).

---

## Step 1 — Create `csv_parser.js`

New file at repo root. Self-contained, exposes one global `window.parseEmotiBitCSV(text, filename)` that returns the full review-data object plus extras for Day Recap.

```js
// csv_parser.js — converts EmotiBit CSV → reviewDataObj-compatible shape
// + Day Recap REPORTS + METERS

(function () {
    // Parse "YYYY-MM-DD_HH-MM-SS-microseconds" out of filename
    function parseStartTime(filename) {
        const m = filename.match(/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})/);
        if (!m) return new Date();
        return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    }

    function parseRows(text) {
        const rows = [];
        const lines = text.split(/\r?\n/);
        for (const line of lines) {
            if (!line) continue;
            const parts = line.split(',');
            if (parts.length < 7) continue;
            const ts = +parts[0];
            const tag = parts[3];
            // numeric values from column 7 onwards
            const vals = [];
            for (let i = 6; i < parts.length; i++) {
                const v = parseFloat(parts[i]);
                if (!isNaN(v)) vals.push(v);
            }
            rows.push({ ts, tag, vals });
        }
        return rows;
    }

    // group {tag → flat array of {tMs, v} where tMs = ts - t0}
    function groupByTag(rows, t0) {
        const out = {};
        for (const r of rows) {
            if (!r.vals.length) continue;
            (out[r.tag] = out[r.tag] || []).push(...r.vals.map(v => ({ tMs: r.ts - t0, v })));
        }
        return out;
    }

    // bucket samples into N-minute bins, average within each bin.
    // returns array of {t: "HH:MM", v: avg, idx} starting at startDate, length nBuckets.
    function bucketize(samples, startDate, bucketMin, nBuckets) {
        const bucketMs = bucketMin * 60_000;
        const sums = new Array(nBuckets).fill(0);
        const counts = new Array(nBuckets).fill(0);
        for (const s of samples) {
            const idx = Math.floor(s.tMs / bucketMs);
            if (idx < 0 || idx >= nBuckets) continue;
            sums[idx] += s.v; counts[idx]++;
        }
        const out = [];
        for (let i = 0; i < nBuckets; i++) {
            const t = new Date(startDate.getTime() + i * bucketMs);
            const hh = String(t.getHours()).padStart(2, '0');
            const mm = String(t.getMinutes()).padStart(2, '0');
            out.push({
                t: `${hh}:${mm}`,
                v: counts[i] ? sums[i] / counts[i] : null,
                idx: i,
            });
        }
        // forward-fill nulls so the sparkline stays continuous
        let last = 0;
        for (const p of out) { if (p.v == null) p.v = last; else last = p.v; }
        return out;
    }

    // crude windowed std-dev for HR (proxy for autonomic arousal)
    function rollingStd(samples, windowMin = 5) {
        // returns same length as samples
        const winMs = windowMin * 60_000;
        const out = [];
        let lo = 0;
        for (let i = 0; i < samples.length; i++) {
            while (samples[lo].tMs < samples[i].tMs - winMs) lo++;
            const slice = samples.slice(lo, i + 1);
            const mean = slice.reduce((a, b) => a + b.v, 0) / slice.length;
            const variance = slice.reduce((a, b) => a + (b.v - mean) ** 2, 0) / slice.length;
            out.push({ tMs: samples[i].tMs, v: Math.sqrt(variance) });
        }
        return out;
    }

    // Map a (cardio, stress, activity) tuple → state name used by Day Recap
    function classifyState(cardio, stress, activity) {
        if (cardio == null) return 'calm';
        if (stress > 70 && cardio > 70) return 'overstimulated';
        if (stress > 60) return 'anxious';
        if (cardio > 70 && activity > 50) return 'active';
        if (cardio > 65) return 'stressed';
        if (cardio < 40 && activity < 20) return 'fatigued';
        return 'calm';
    }

    // Produce REPORTS array (one per 30-min slot covering the recording window)
    function buildReports(cardio30, stress30, activity30) {
        const TEMPLATES = {
            calm: ['Steady rhythm. Body and mind in alignment.', 'Quiet baseline. Breath even.', 'Settled. Low arousal, clear signal.'],
            stressed: ['Stress signals rising. Breath shorter.', 'Elevated load — system pushing.', 'Heart climbing, tension lingering.'],
            anxious: ['Restless undertone. Hands fidgeting maybe.', 'Vibration beneath the surface.', 'Mind ahead of the body.'],
            active: ['Movement and warmth. Energy outward.', 'Engaged, kinetic. Heart open.', 'Activity burst — body in flow.'],
            fatigued: ['Energy dipping. Glow lower.', 'Heaviness across the shoulders.', 'Recovery needed.'],
            overstimulated: ['Too many inputs at once.', 'Signal saturated. Hard to filter.', 'System overloaded, edges fraying.'],
        };
        const QUESTIONS = {
            calm: 'What were you sensing then?',
            stressed: 'What happened around then?',
            anxious: 'What was on your mind?',
            active: 'Were you moving around?',
            fatigued: 'When did you last rest?',
            overstimulated: 'What was around you?',
        };
        return cardio30.map((c, i) => {
            const s = stress30[i].v, a = activity30[i].v;
            const state = classifyState(c.v, s, a);
            const tpl = TEMPLATES[state];
            return {
                t: c.t,
                state,
                text: tpl[i % tpl.length],
                question: QUESTIONS[state],
                mockAnswer: '',
            };
        });
    }

    function buildMeters(cardioAvg, stressAvg, activityAvg, baselines) {
        const cardioDelta = baselines.cardio ? Math.round(((cardioAvg - baselines.cardio) / baselines.cardio) * 100) : 0;
        const stressDelta = baselines.stress ? Math.round(((stressAvg - baselines.stress) / baselines.stress) * 100) : 0;
        const activityDelta = baselines.activity ? Math.round(((activityAvg - baselines.activity) / baselines.activity) * 100) : 0;
        const sign = n => (n >= 0 ? '+' : '') + n + '% vs week';
        return [
            { id: 'cardio',   title: 'Cardiovascular Load', value: Math.round(cardioAvg),   ringPct: cardioAvg / 100,   color: '#FF6B61', evalText: cardioAvg < 40 ? 'Low Load' : cardioAvg > 60 ? 'High Load' : 'Normal Load', vsWeek: sign(cardioDelta) },
            { id: 'stress',   title: 'Stress & Arousal',    value: Math.round(stressAvg),   ringPct: stressAvg / 100,   color: '#FFB75A', evalText: stressAvg < 30 ? 'Low Stress' : stressAvg > 60 ? 'High Stress' : 'Normal Stress', vsWeek: sign(stressDelta) },
            { id: 'activity', title: 'Activity level',      value: Math.round(activityAvg), ringPct: activityAvg / 100, color: '#7FE8FF', evalText: activityAvg < 30 ? 'Low activity' : activityAvg > 60 ? 'High activity' : 'Moderate activity', vsWeek: sign(activityDelta) },
        ];
    }

    // ── Public ─────────────────────────────────────────────────────────
    window.parseEmotiBitCSV = function (text, filename) {
        const startDate = parseStartTime(filename);
        const rows = parseRows(text);
        if (!rows.length) throw new Error('Empty CSV');
        const t0 = rows[0].ts;
        const tEnd = rows[rows.length - 1].ts;
        const durationMs = tEnd - t0;

        const grouped = groupByTag(rows, t0);

        // ── Cardio score from HR (clamp 40–120 → 0–100) ───────────────
        const hrSamples = grouped['HR'] || [];
        const hrToScore = hr => Math.max(0, Math.min(100, ((hr - 40) / 80) * 100));
        const cardioRaw = hrSamples.map(s => ({ tMs: s.tMs, v: hrToScore(s.v) }));

        // ── Stress score from rolling HR variability + EDA (SF) ───────
        const sfSamples = grouped['SF'] || [];
        const hrStd = rollingStd(hrSamples, 5);
        const hrStdScore = hrStd.map(s => ({ tMs: s.tMs, v: Math.max(0, Math.min(100, s.v * 8)) }));
        const sfMin = sfSamples.length ? Math.min(...sfSamples.map(s => s.v)) : 0;
        const sfMax = sfSamples.length ? Math.max(...sfSamples.map(s => s.v)) : 1;
        const sfRange = (sfMax - sfMin) || 1;
        const sfScore = sfSamples.map(s => ({ tMs: s.tMs, v: ((s.v - sfMin) / sfRange) * 100 }));
        // Average the two streams into one stress curve
        const stressRaw = mergeStreams(hrStdScore, sfScore);

        // ── Activity score from accelerometer magnitude ───────────────
        const ax = grouped['AX'] || [], ay = grouped['AY'] || [], az = grouped['AZ'] || [];
        const activityRaw = [];
        const n = Math.min(ax.length, ay.length, az.length);
        for (let i = 0; i < n; i++) {
            const mag = Math.sqrt(ax[i].v ** 2 + ay[i].v ** 2 + az[i].v ** 2);
            // resting magnitude ≈ 1g; deviations represent motion
            activityRaw.push({ tMs: ax[i].tMs, v: Math.max(0, Math.min(100, Math.abs(mag - 1) * 200)) });
        }

        // Bucket sizes:
        //   - 5-min for sparklines (matches existing curve shape)
        //   - 30-min for Day Recap REPORTS
        const minutes = durationMs / 60_000;
        const n5  = Math.max(1, Math.ceil(minutes / 5));
        const n30 = Math.max(1, Math.ceil(minutes / 30));

        const cardio5  = bucketize(cardioRaw,  startDate, 5,  n5);
        const stress5  = bucketize(stressRaw,  startDate, 5,  n5);
        const cardio30 = bucketize(cardioRaw,  startDate, 30, n30);
        const stress30 = bucketize(stressRaw,  startDate, 30, n30);
        const activ30  = bucketize(activityRaw, startDate, 30, n30);

        const avg = arr => arr.length ? arr.reduce((a, b) => a + b.v, 0) / arr.length : 0;
        const cardioAvg = avg(cardio5);
        const stressAvg = avg(stress5);
        const activityAvg = avg(bucketize(activityRaw, startDate, 5, n5));

        const cardioPeak = cardio5.reduce((m, p) => p.v > m ? p.v : m, 0);
        const stressPeak = stress5.reduce((m, p) => p.v > m ? p.v : m, 0);

        const dominantState = classifyState(cardioAvg, stressAvg, activityAvg);
        const TAGLINES = {
            calm: 'Your body is in a state of calm balance.',
            stressed: 'Your body carried real load today.',
            anxious: 'A restless current ran beneath today.',
            active: 'Your body moved with intent today.',
            fatigued: 'Your body is asking for rest.',
            overstimulated: 'A lot came at you today.',
        };

        const reviewObj = {
            date: startDate.toISOString().slice(0, 10),
            user_id: 'emotibit_user',
            summary: {
                cardio_avg: Math.round(cardioAvg),
                cardio_vs_baseline_pct: 0,
                cardio_peak_historical: Math.round(cardioPeak),
                cardio_peak_date: '—',
                stress_avg: Math.round(stressAvg),
                stress_vs_baseline_pct: 0,
                stress_peak_historical: Math.round(stressPeak),
                stress_peak_date: '—',
                dominant_state: dominantState,
                tagline: TAGLINES[dominantState],
            },
            dashboards: {
                cardio: {
                    label: 'Cardiovascular Load', unit: 'score',
                    curve: cardio5.map(p => ({ t: p.t, v: Math.round(p.v) })),
                    baseline_line: 50,
                    highlights: findHighlights(cardio5, 'cardio'),
                    gauge: { value: Math.round(cardioAvg), fill_pct: cardioAvg / 100, delta_pct: 0 },
                },
                stress: {
                    label: 'Stress & Arousal', unit: 'score',
                    curve: stress5.map(p => ({ t: p.t, v: Math.round(p.v) })),
                    baseline_line: 40,
                    highlights: findHighlights(stress5, 'stress'),
                    gauge: { value: Math.round(stressAvg), fill_pct: stressAvg / 100, delta_pct: 0 },
                },
            },
            questions: buildQuestions(cardio5, stress5),
        };

        const reports = buildReports(cardio30, stress30, activ30);
        const meters  = buildMeters(cardioAvg, stressAvg, activityAvg, { cardio: 50, stress: 40, activity: 30 });

        return {
            review: reviewObj,
            reports,
            meters,
            startDate,
            endDate: new Date(startDate.getTime() + durationMs),
            durationHours: durationMs / 3_600_000,
        };
    };

    // helpers below: mergeStreams, findHighlights, buildQuestions
    // (implementations: simple — see notes in Step 1 below)
})();
```

### Helpers — keep small

- **`mergeStreams(a, b)`**: concat both arrays, sort by `tMs`. Don't bother averaging across streams — the bucketizer will smooth them when it bins.
- **`findHighlights(curve5, metric)`**: find runs of ≥3 consecutive 5-min buckets that are >25 % above the mean. Return at most 3, shape:
  ```js
  { metric, id: `${metric}.${k}`, start: curve5[i0].t, end: curve5[iN].t,
    peak: Math.round(maxV), pct_above_mean: Math.round((maxV - mean) / mean * 100),
    duration_min: (iN - i0 + 1) * 5, start_idx: i0 }
  ```
- **`buildQuestions(cardio5, stress5)`**: simple — return one generic question per highlight, plus one anchor question:
  ```js
  [ { id: 'overall', category: 'reflect', text: 'How do you remember today landing in your body?', linked_highlight: null } ]
  ```
  Add one extra question per highlight: `Your cardio rose between {start} and {end}. Was that movement, stress, or something else?`

These helpers are intentionally trivial — the goal is to fill the renderers' slots with plausible derived values, not to do clinical analytics.

---

## Step 2 — Wire the parser into `ui_mockup.html`

### 2a. Load the parser script

In `<head>` (around line 22, next to the other module scripts), add:

```html
<script src="./csv_parser.js"></script>
```

Do **not** remove the `<script src="./review_data.js"></script>` at line 1457 — keep it as a final fallback.

### 2b. Add a CSV constant + mock toggle

Right after the parser script tag, define the target CSV filename and read the persisted mode from `localStorage` so the user can flip between real CSV and mock data with a key press:

```html
<script>
    window.REVIEW_CSV_DEFAULT = './2026-04-25_11-32-15-268408.csv';
    // Persisted mode: 'csv' (default) or 'mock'. Pressing M toggles + reloads.
    window.REVIEW_MODE = localStorage.getItem('reviewMode') || 'csv';
    window.REVIEW_CSV_PATH = (window.REVIEW_MODE === 'mock') ? null : window.REVIEW_CSV_DEFAULT;
</script>
```

### 2b-bis. Wire the `M` key to toggle modes

Inside the main `<script>` block (alongside the existing `D`-key handler at line ~1766), add a new keydown handler:

```js
// ─── Mock-mode toggle (M key) — flips between real CSV and reviewDataObj ──
document.addEventListener('keydown', (e) => {
    if (e.key !== 'm' && e.key !== 'M') return;
    // Ignore if user is typing in a textarea/input
    if (e.target.matches('input, textarea')) return;
    const next = (localStorage.getItem('reviewMode') === 'mock') ? 'csv' : 'mock';
    localStorage.setItem('reviewMode', next);
    // Brief toast so the user knows what just happened
    const toast = document.createElement('div');
    toast.textContent = `Switching to ${next.toUpperCase()} data…`;
    toast.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: rgba(0,0,0,0.85); color: #F5F5F7;
        padding: 1rem 2rem; border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.2);
        font-family: 'Outfit', sans-serif; font-weight: 200;
        letter-spacing: 0.12em; text-transform: uppercase;
        font-size: 0.9rem; z-index: 9999;
        backdrop-filter: blur(12px);
    `;
    document.body.appendChild(toast);
    setTimeout(() => location.reload(), 600);
});
```

The toggle persists across reloads via `localStorage`, so once you press `M` to switch to mock, every subsequent load stays in mock until you press `M` again. No visible UI required.

### 2c. Stash parsed extras on `window`

The Day Recap module reads `REPORTS` and `METERS` as module-private constants. Easiest path: change them from `const` to `let`, and overwrite them from a global before `dayRecap.init()` runs. Add at the top of the `<script>` block (line ~1458, just after `gsap.registerPlugin(...)`):

```js
window.csvParsed = null;  // populated by loadReview() if CSV available
```

### 2d. Replace `loadReview()` (line ~2190)

```js
async function loadReview() {
    // 1) Try real CSV first
    if (window.parseEmotiBitCSV && window.REVIEW_CSV_PATH) {
        try {
            const res = await fetch(window.REVIEW_CSV_PATH);
            if (res.ok) {
                const text = await res.text();
                const filename = window.REVIEW_CSV_PATH.split('/').pop();
                window.csvParsed = window.parseEmotiBitCSV(text, filename);
                applyReview(window.csvParsed.review);
                return;
            }
        } catch (e) {
            console.warn('CSV load failed, falling back:', e);
        }
    }
    // 2) Try review.json
    try {
        const res = await fetch('./review.json');
        if (res.ok) { applyReview(await res.json()); return; }
    } catch (e) {}
    // 3) Fallback to embedded reviewDataObj
    if (typeof reviewDataObj !== 'undefined') applyReview(reviewDataObj);
    else console.error('No review data available.');
}

function applyReview(data) {
    renderDashboards(data);
    renderQuestions(data);
    const h2 = document.querySelector('#scene-review h2');
    if (h2 && data.summary && data.summary.tagline) h2.textContent = data.summary.tagline;
}
```

### 2e. Make `REPORTS` and `METERS` overridable in `dayRecap` module

Around line 2355 and 2380, change:
```js
const REPORTS = [ ... ];
const METERS = [ ... ];
```
to:
```js
let REPORTS = [ ... ];   // default mock
let METERS  = [ ... ];   // default mock
```

In `dayRecap`'s public API (`return { ... }` at line ~2104-equivalent for dayRecap — find the matching `return { init() ... }` block in the dayRecap IIFE), add an `applyParsed` method, **or** simply have `init()` look at `window.csvParsed` and overwrite the locals before render. The simpler edit: at the very top of `dayRecap.init()` (find it; it calls `_resolveEls()` then `_renderMeters()`/`_renderReports()`), add:

```js
if (window.csvParsed) {
    if (window.csvParsed.reports && window.csvParsed.reports.length)  REPORTS = window.csvParsed.reports;
    if (window.csvParsed.meters  && window.csvParsed.meters.length)   METERS  = window.csvParsed.meters;
}
```

### 2f. Out-banner duration text

The Day Recap shows `<strong id="dr-out-hours">10 hours long!</strong>`. Replace it from CSV when available. Inside `dayRecap.init()`, after the `csvParsed` check above:

```js
if (window.csvParsed && els.outHours) {
    const h = window.csvParsed.durationHours;
    els.outHours.textContent = `${h.toFixed(1)} hours long!`;
}
```

### 2g. Scrubber tick range (`_renderScrubber`, line ~2468)

Currently hardcoded `8:00`–`18:00`. Replace its first lines so the start/end follow the real recording window when available:

```js
function _renderScrubber() {
    let startMin = 8 * 60, endMin = 18 * 60;
    if (window.csvParsed) {
        const s = window.csvParsed.startDate;
        const e = window.csvParsed.endDate;
        startMin = s.getHours() * 60 + s.getMinutes();
        endMin   = e.getHours() * 60 + e.getMinutes();
    }
    const span = endMin - startMin;
    // pick ~6 evenly spaced major ticks rounded to the hour
    const majors = [];
    const startHr = Math.ceil(startMin / 60);
    const endHr   = Math.floor(endMin / 60);
    const step    = Math.max(1, Math.ceil((endHr - startHr) / 5));
    for (let h = startHr; h <= endHr; h += step) majors.push(`${h}:00`);
    els.scrubTrack.querySelectorAll('.dr-scrub-tick').forEach(n => n.remove());
    majors.forEach(label => {
        const [h, m] = label.split(':').map(Number);
        const pct = ((h * 60 + m) - startMin) / span;
        const t = document.createElement('div');
        t.className = 'dr-scrub-tick major';
        t.textContent = label;
        t.style.top = (pct * 100) + '%';
        els.scrubTrack.appendChild(t);
    });
}
```

---

## Step 3 — Verify

1. Open `ui_mockup.html` in a browser served via local HTTP (`python -m http.server` in the project dir — `fetch()` won't work on `file://`).
2. The Daily Review should show:
   - Tagline reflecting the dominant state computed from the CSV.
   - Two sparklines (cardio + stress) with the real-data shape, not the static curves.
   - Gauge values matching the CSV averages.
3. Press through to Day Recap — the meters, scrubber labels (`11:00`-ish to `19:00`-ish), report cards, and out-banner ("≈8.5 hours long!") should reflect the recording.
4. Biofeedback challenge should still launch unchanged.
5. If the CSV fetch fails (e.g. opened via `file://`), falls back silently to `reviewDataObj`. Confirm with DevTools network tab that the CSV was requested.

## Step 4 — Done. What NOT to do

- Do **not** edit `biosignal.js` — the biofeedback challenge has its own data source.
- Do **not** rewrite the renderers (`renderDashboards`, `renderQuestions`, `_renderMeters`, `_renderReports`). Keep the data shape compatible.
- Do **not** delete `review_data.js`. It's the offline fallback.
- Do **not** add new UI controls (file pickers, etc.) for selecting the CSV. Use the hardcoded `REVIEW_CSV_PATH` for now.
- Do **not** invent baselines. Set `cardio_vs_baseline_pct: 0` and similar deltas to `0` (or `null`) until real historical data exists. The renderer tolerates `0`.

## Edge cases worth handling

- CSV has gaps (no HR for ~50 min stretch around row 16641 → 16920). The `bucketize` forward-fill keeps the curve continuous; that's fine.
- Some `HR` values are obviously wrong (`48.59` followed by `79.46` 320 ms apart). Don't try to clean — averaging over 5-min buckets dampens noise enough.
- Very short recordings (<30 min): `n30` will be 1, so `REPORTS` will have a single card. Acceptable — don't special-case.
- Filename without timestamp: `parseStartTime` falls back to `new Date()`. Acceptable.
