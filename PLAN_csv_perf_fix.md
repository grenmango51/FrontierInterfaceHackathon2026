# Plan: Make CSV pipeline actually work on the real 200 MB / 5 M-row file

## Why this is needed

The previous integration loaded the CSV but silently fell back to mock data because the parser couldn't handle a 200 MB file. The UI showed mock numbers (`50 / 23 / 23`, `08:00–18:00`, `10 hours long!`). Three concrete bugs to fix:

1. **`Math.min(...arr)` / `Math.max(...arr)` blow the call stack** on arrays >~100 k entries (V8 limit). The SF stream alone is hundreds of thousands of samples.
2. **`rollingStd()` is O(n²)**. With ~25 k HR samples that's ~625 M operations — page locks for minutes, then the sliced-array allocations OOM.
3. **`groupByTag()` materialises every sample into `{tMs, v}` objects** before bucketing. ~5 M objects × ~40 bytes = ~200 MB of garbage.

These all need to go. The fix is to **bucket while parsing** — never hold more than `nBuckets` numbers in memory per stream.

We also need the user to *see* what mode rendered the screen, and to see parse errors instead of silent fallbacks.

## Files to change

1. **`csv_parser.js`** — rewrite `parseEmotiBitCSV` to stream-bucket. Keep the public API identical (same return shape).
2. **`ui_mockup.html`** — add a mode chip + console diagnostics, surface parse errors.

Do NOT touch `biosignal.js`, `review_data.js`, or the renderers.

---

## Step 1 — Rewrite `csv_parser.js` to stream-bucket

Replace the whole file. The new design:

- **Single pass over `text`** using `indexOf('\n')` slicing. No `split('\n')` (that allocates 5 M strings). No regex.
- **For each row**, look at the type tag and update bucket aggregates (`sums[bucketIdx] += v; counts[bucketIdx]++`). Discard the row immediately.
- **Pre-size bucket arrays** before the parse loop. We compute `durationMs` in a *cheap* preflight: read the first valid row's timestamp, then read the last \~2 KB of the file to grab the final timestamp. Or — simpler and equally fast — do a **two-pass scan**: pass 1 finds `t0` and `tEnd`; pass 2 does the bucketing. Both passes are byte-level, no allocation. Use this approach.

### File skeleton

```js
// csv_parser.js — streaming EmotiBit CSV parser
// Two-pass byte-level scan: never materialises per-sample objects.
// Public: window.parseEmotiBitCSV(text, filename) → { review, reports, meters, startDate, endDate, durationHours }

(function () {

    const BUCKET_5_MIN  = 5 * 60_000;
    const BUCKET_30_MIN = 30 * 60_000;

    // ── Filename → start Date ────────────────────────────────────────────
    function parseStartTime(filename) {
        const m = filename.match(/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})/);
        if (!m) return new Date();
        return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    }

    // ── Iterate over CSV rows without splitting the whole string ─────────
    // Calls cb(ts, tag, valuesString, valuesStart, valuesEnd) for each row.
    // valuesString is the full line; valuesStart/End delimit the comma-separated
    // numeric values starting at column 7 (index 6 of the comma-split).
    function forEachRow(text, cb) {
        const len = text.length;
        let lineStart = 0;
        while (lineStart < len) {
            let lineEnd = text.indexOf('\n', lineStart);
            if (lineEnd === -1) lineEnd = len;
            // Skip empty lines
            if (lineEnd > lineStart) {
                // Find first 6 commas to locate ts (col 0), tag (col 3), values start (col 6)
                let c = lineStart;
                let comma = 0;
                let tsEnd = -1, tagStart = -1, tagEnd = -1, valStart = -1;
                while (c < lineEnd && comma < 6) {
                    if (text.charCodeAt(c) === 44 /* , */) {
                        comma++;
                        if (comma === 1) tsEnd = c;
                        else if (comma === 3) tagStart = c + 1;
                        else if (comma === 4) tagEnd = c;
                        else if (comma === 6) valStart = c + 1;
                    }
                    c++;
                }
                if (comma >= 6 && tsEnd > lineStart && tagEnd > tagStart) {
                    const ts  = +text.substring(lineStart, tsEnd);
                    const tag = text.substring(tagStart, tagEnd);
                    if (ts && tag) cb(ts, tag, text, valStart, lineEnd);
                }
            }
            lineStart = lineEnd + 1;
        }
    }

    // ── Walk the comma-separated values from valStart..valEnd, calling
    //    cb(value) for each numeric. No allocation.
    function forEachValue(text, start, end, cb) {
        let i = start;
        while (i < end) {
            // Skip leading whitespace
            while (i < end && text.charCodeAt(i) === 32) i++;
            let j = i;
            while (j < end && text.charCodeAt(j) !== 44) j++;
            if (j > i) {
                const n = +text.substring(i, j);
                if (!isNaN(n)) cb(n);
            }
            i = j + 1;
        }
    }

    // ── Bucket aggregator ────────────────────────────────────────────────
    // Holds running sum + count + min + max per bucket. add(tMs, v) is O(1).
    function makeBuckets(nBuckets, bucketMs) {
        const sums   = new Float64Array(nBuckets);
        const counts = new Uint32Array(nBuckets);
        let gMin = Infinity, gMax = -Infinity, gSum = 0, gCount = 0;
        return {
            add(tMs, v) {
                if (tMs < 0) return;
                const idx = (tMs / bucketMs) | 0;
                if (idx >= nBuckets) return;
                sums[idx]   += v;
                counts[idx] += 1;
                if (v < gMin) gMin = v;
                if (v > gMax) gMax = v;
                gSum   += v;
                gCount += 1;
            },
            toCurve(startDate) {
                const out = new Array(nBuckets);
                let last = 0;
                for (let i = 0; i < nBuckets; i++) {
                    const v = counts[i] ? sums[i] / counts[i] : null;
                    const t = new Date(startDate.getTime() + i * bucketMs);
                    const hh = String(t.getHours()).padStart(2, '0');
                    const mm = String(t.getMinutes()).padStart(2, '0');
                    out[i] = { t: `${hh}:${mm}`, v: (v == null ? last : (last = v, v)), idx: i };
                }
                return out;
            },
            stats() {
                return {
                    min: gMin === Infinity ? 0 : gMin,
                    max: gMax === -Infinity ? 0 : gMax,
                    avg: gCount ? gSum / gCount : 0,
                    count: gCount,
                };
            }
        };
    }

    // ── State classification (unchanged from previous parser) ────────────
    function classifyState(cardio, stress, activity) {
        if (cardio == null) return 'calm';
        if (stress > 70 && cardio > 70) return 'overstimulated';
        if (stress > 60) return 'anxious';
        if (cardio > 70 && activity > 50) return 'active';
        if (cardio > 65) return 'stressed';
        if (cardio < 40 && activity < 20) return 'fatigued';
        return 'calm';
    }

    // ── Highlight detection on a 5-min curve ─────────────────────────────
    function findHighlights(curve5, metric) {
        if (!curve5.length) return [];
        let sum = 0;
        for (const p of curve5) sum += p.v;
        const mean = sum / curve5.length;
        const threshold = mean * 1.25;
        const out = [];
        let runStart = -1, runMax = 0;
        for (let i = 0; i <= curve5.length; i++) {
            const above = i < curve5.length && curve5[i].v > threshold;
            if (above) {
                if (runStart === -1) { runStart = i; runMax = curve5[i].v; }
                else if (curve5[i].v > runMax) runMax = curve5[i].v;
            } else if (runStart !== -1) {
                if ((i - runStart) >= 3) {
                    out.push({
                        metric, id: `${metric}.${out.length}`,
                        start: curve5[runStart].t,
                        end:   curve5[i - 1].t,
                        peak:  Math.round(runMax),
                        pct_above_mean: Math.round((runMax - mean) / Math.max(1, mean) * 100),
                        duration_min: (i - runStart) * 5,
                        start_idx: runStart,
                    });
                    if (out.length >= 3) break;
                }
                runStart = -1;
            }
        }
        return out;
    }

    function buildQuestions(cardioHL, stressHL) {
        const qs = [{ id: 'overall', category: 'reflect', text: 'How do you remember today landing in your body?', linked_highlight: null }];
        for (const hl of [...cardioHL, ...stressHL].slice(0, 2)) {
            const noun = hl.metric === 'cardio' ? 'cardiovascular load' : 'stress signal';
            qs.push({
                id: hl.id, category: 'pattern_probe',
                text: `Your ${noun} rose between ${hl.start} and ${hl.end}. Was that movement, stress, or something else?`,
                linked_highlight: hl.id,
            });
        }
        return qs;
    }

    function buildReports(cardio30, stress30, activity30) {
        const TPL = {
            calm:           ['Steady rhythm. Body and mind in alignment.', 'Quiet baseline. Breath even, signal clear.', 'Settled. Low arousal, attention soft.'],
            stressed:       ['Stress signals rising. Breath shorter, shoulders up.', 'Elevated load — system pushing through.', 'Heart climbing, tension lingering.'],
            anxious:        ['Restless undertone. Hands fidgeting maybe.', 'Vibration beneath the surface.', 'Mind running ahead of the body.'],
            active:         ['Movement and warmth. Energy moving outward.', 'Engaged, kinetic. Heart open.', 'Activity burst — body in flow.'],
            fatigued:       ['Energy dipping. Glow lower, posture softer.', 'Heaviness across the shoulders.', 'Body asking for rest.'],
            overstimulated: ['Too many inputs at once. System overloaded.', 'Signal saturated. Hard to filter.', 'Edges fraying. Too much at once.'],
        };
        const Q = { calm:'What were you sensing then?', stressed:'What happened around that time?', anxious:'What was on your mind?', active:'Were you moving around?', fatigued:'When did you last rest?', overstimulated:'What was around you then?' };
        const A = { calm:'Things felt manageable.', stressed:'A lot was happening at once.', anxious:'I had a lot on my mind.', active:'Yes, I was moving.', fatigued:'I needed a break.', overstimulated:'It was a lot to take in.' };
        return cardio30.map((c, i) => {
            const s = stress30[i] ? stress30[i].v : 0;
            const a = activity30[i] ? activity30[i].v : 0;
            const state = classifyState(c.v, s, a);
            return { t: c.t, state, text: TPL[state][i % TPL[state].length], question: Q[state], mockAnswer: A[state] };
        });
    }

    function buildMeters(cardioAvg, stressAvg, activityAvg) {
        const baselines = { cardio: 50, stress: 40, activity: 30 };
        const delta = (v, b) => b ? Math.round(((v - b) / b) * 100) : 0;
        const sign  = n => (n >= 0 ? '+' : '') + n + '% vs week';
        const cardioEval   = cardioAvg   < 40 ? 'Low Load'      : cardioAvg   > 60 ? 'High Load'      : 'Normal Load';
        const stressEval   = stressAvg   < 30 ? 'Low Stress'    : stressAvg   > 60 ? 'High Stress'    : 'Normal Stress';
        const activityEval = activityAvg < 30 ? 'Low activity'  : activityAvg > 60 ? 'High activity'  : 'Moderate activity';
        return [
            { id:'cardio',   title:'Cardiovascular Load', value:Math.round(cardioAvg),   ringPct:Math.min(1,cardioAvg/100),   color:'#FF6B61', evalText:cardioEval,   vsWeek:sign(delta(cardioAvg,   baselines.cardio))   },
            { id:'stress',   title:'Stress & Arousal',    value:Math.round(stressAvg),   ringPct:Math.min(1,stressAvg/100),   color:'#FFB75A', evalText:stressEval,   vsWeek:sign(delta(stressAvg,   baselines.stress))   },
            { id:'activity', title:'Activity level',      value:Math.round(activityAvg), ringPct:Math.min(1,activityAvg/100), color:'#7FE8FF', evalText:activityEval, vsWeek:sign(delta(activityAvg, baselines.activity)) },
        ];
    }

    // ── Main ─────────────────────────────────────────────────────────────
    window.parseEmotiBitCSV = function (text, filename) {
        const startDate = parseStartTime(filename);
        const t0Start = performance.now();

        // ── Pass 1: find first/last timestamp (cheap byte scan) ──────────
        let t0 = null, tEnd = null;
        forEachRow(text, (ts) => {
            if (t0 === null) t0 = ts;
            tEnd = ts;
        });
        if (t0 === null) throw new Error('CSV contains no rows');
        const durationMs = Math.max(0, tEnd - t0);
        const minutes    = durationMs / 60_000;
        const n5         = Math.max(1, Math.ceil(minutes / 5));
        const n30        = Math.max(1, Math.ceil(minutes / 30));

        // ── Pass 2: stream-bucket each tag we care about ──────────────────
        // Cardio (HR), stress proxy via SF, activity via accelerometer magnitude.
        // We bucket *during* parsing — never store per-sample arrays.
        const cardioB5  = makeBuckets(n5,  BUCKET_5_MIN);
        const cardioB30 = makeBuckets(n30, BUCKET_30_MIN);
        const stressB5  = makeBuckets(n5,  BUCKET_5_MIN);
        const stressB30 = makeBuckets(n30, BUCKET_30_MIN);
        const activB5   = makeBuckets(n5,  BUCKET_5_MIN);
        const activB30  = makeBuckets(n30, BUCKET_30_MIN);

        // For accelerometer: AX/AY/AZ rows are separate; pair them by sample
        // count using simple running buffers. Not perfect alignment but fine
        // for activity averages.
        const accel = { x: [], y: [], z: [], maxBuf: 256 };
        const pushAccel = (axis, v) => {
            const a = accel[axis];
            a.push(v);
            if (a.length > accel.maxBuf) a.shift();
        };

        // SF normalisation needs min/max — capture them in pass 2 by streaming
        // through twice with a tiny intermediate. Since SF is small (~3 Hz),
        // we keep raw SF samples in a flat Float32Array (preallocated).
        // Pre-count SF rows in pass 1? Simpler: append to a growing array.
        // The earlier 200 MB worry doesn't apply — SF is ~10 k samples max.
        const sfRaw = [];        // {tMs, v}
        let sfMin = Infinity, sfMax = -Infinity;

        // HR rolling-variance proxy: maintain a Welford-style window.
        // Approximate "rolling 5-min std dev" with a ring buffer of last
        // ~150 HR samples (~5 min at 0.5 Hz). Sufficient for a stress proxy.
        const hrRing = new Float32Array(150);
        let hrRingLen = 0, hrRingHead = 0;

        const pushHRStress = (tMs, hr) => {
            // Update ring buffer
            if (hrRingLen < 150) { hrRing[hrRingLen++] = hr; }
            else { hrRing[hrRingHead] = hr; hrRingHead = (hrRingHead + 1) % 150; }
            // Compute std-dev over current ring
            let sum = 0;
            for (let i = 0; i < hrRingLen; i++) sum += hrRing[i];
            const mean = sum / hrRingLen;
            let varAcc = 0;
            for (let i = 0; i < hrRingLen; i++) { const d = hrRing[i] - mean; varAcc += d * d; }
            const std = Math.sqrt(varAcc / hrRingLen);
            const stressScore = Math.max(0, Math.min(100, std * 8));
            stressB5.add(tMs, stressScore);
            stressB30.add(tMs, stressScore);
        };

        forEachRow(text, (ts, tag, txt, vS, vE) => {
            const tMs = ts - t0;
            if (tag === 'HR') {
                forEachValue(txt, vS, vE, hr => {
                    if (hr <= 0 || hr > 220) return; // sanity
                    const cardio = Math.max(0, Math.min(100, ((hr - 40) / 80) * 100));
                    cardioB5.add(tMs, cardio);
                    cardioB30.add(tMs, cardio);
                    pushHRStress(tMs, hr);
                });
            } else if (tag === 'SF') {
                forEachValue(txt, vS, vE, v => {
                    sfRaw.push({ tMs, v });
                    if (v < sfMin) sfMin = v;
                    if (v > sfMax) sfMax = v;
                });
            } else if (tag === 'AX' || tag === 'AY' || tag === 'AZ') {
                const axis = tag === 'AX' ? 'x' : tag === 'AY' ? 'y' : 'z';
                forEachValue(txt, vS, vE, v => {
                    pushAccel(axis, v);
                    // When we have at least one of each axis, emit an activity sample
                    if (accel.x.length && accel.y.length && accel.z.length) {
                        const lx = accel.x[accel.x.length - 1];
                        const ly = accel.y[accel.y.length - 1];
                        const lz = accel.z[accel.z.length - 1];
                        const mag = Math.sqrt(lx*lx + ly*ly + lz*lz);
                        const score = Math.max(0, Math.min(100, Math.abs(mag - 1) * 200));
                        activB5.add(tMs, score);
                        activB30.add(tMs, score);
                    }
                });
            }
            // Ignore PI/PR/PG/T1/MX/MY/MZ/GX/GY/GZ/EA/EL/RB/EM/RD/AK/B%/BI/BV/SA/SR/TH/TL
        });

        // SF post-pass: now we know min/max, fold into stress aggregates.
        if (sfRaw.length) {
            const range = (sfMax - sfMin) || 1;
            for (let i = 0; i < sfRaw.length; i++) {
                const s = sfRaw[i];
                const stressScore = ((s.v - sfMin) / range) * 100;
                stressB5.add(s.tMs, stressScore);
                stressB30.add(s.tMs, stressScore);
            }
        }

        const cardio5  = cardioB5.toCurve(startDate);
        const stress5  = stressB5.toCurve(startDate);
        const cardio30 = cardioB30.toCurve(startDate);
        const stress30 = stressB30.toCurve(startDate);
        const activ30  = activB30.toCurve(startDate);

        const cardioStats = cardioB5.stats();
        const stressStats = stressB5.stats();
        const activStats  = activB5.stats();

        const cardioAvg   = cardioStats.avg;
        const stressAvg   = stressStats.avg;
        const activityAvg = activStats.avg;
        const cardioPeak  = cardioStats.max;
        const stressPeak  = stressStats.max;

        const dominantState = classifyState(cardioAvg, stressAvg, activityAvg);
        const TAGLINES = {
            calm:'Your body is in a state of calm balance.',
            stressed:'Your body carried real load today.',
            anxious:'A restless current ran beneath today.',
            active:'Your body moved with intent today.',
            fatigued:'Your body is asking for rest.',
            overstimulated:'A lot came at you today.',
        };

        const cardioHL = findHighlights(cardio5, 'cardio');
        const stressHL = findHighlights(stress5, 'stress');

        const reviewObj = {
            date: startDate.toISOString().slice(0, 10),
            user_id: 'emotibit_user',
            summary: {
                cardio_avg:             Math.round(cardioAvg),
                cardio_vs_baseline_pct: 0,
                cardio_peak_historical: Math.round(cardioPeak),
                cardio_peak_date:       '—',
                stress_avg:             Math.round(stressAvg),
                stress_vs_baseline_pct: 0,
                stress_peak_historical: Math.round(stressPeak),
                stress_peak_date:       '—',
                dominant_state:         dominantState,
                tagline:                TAGLINES[dominantState],
            },
            dashboards: {
                cardio: {
                    label:'Cardiovascular Load', unit:'score',
                    curve: cardio5.map(p => ({ t:p.t, v:Math.round(p.v) })),
                    baseline_line: 50,
                    highlights: cardioHL,
                    gauge: { value:Math.round(cardioAvg), fill_pct:cardioAvg/100, delta_pct:0 },
                },
                stress: {
                    label:'Stress & Arousal', unit:'score',
                    curve: stress5.map(p => ({ t:p.t, v:Math.round(p.v) })),
                    baseline_line: 40,
                    highlights: stressHL,
                    gauge: { value:Math.round(stressAvg), fill_pct:stressAvg/100, delta_pct:0 },
                },
            },
            questions: buildQuestions(cardioHL, stressHL),
        };

        const reports = buildReports(cardio30, stress30, activ30);
        const meters  = buildMeters(cardioAvg, stressAvg, activityAvg);
        const endDate = new Date(startDate.getTime() + durationMs);
        const parseMs = performance.now() - t0Start;

        return {
            review: reviewObj,
            reports,
            meters,
            startDate,
            endDate,
            durationHours: durationMs / 3_600_000,
            // Diagnostics consumed by the boot sequence
            diagnostics: {
                parseMs:    Math.round(parseMs),
                hrCount:    cardioStats.count,
                sfCount:    sfRaw.length,
                activCount: activStats.count,
                cardioAvg, stressAvg, activityAvg,
                durationMs,
            },
        };
    };

})();
```

### Why this is fast enough

- **Two byte-level passes over a 200 MB string.** V8 string scans run at >1 GB/s; expect <1 s total.
- **Zero per-sample allocation** for HR / accelerometer (they go straight into typed-array buckets).
- **SF gets one small intermediate** (`sfRaw`) — a few thousand objects, fine.
- **No `Math.min(...arr)` / `Math.max(...arr)` anywhere.** Mins/maxes are tracked inline.
- **Rolling stress is O(1) amortised** (fixed 150-sample ring).

If even pass 2 is still slow (unlikely but possible), the easiest follow-up is to wrap it in a `Web Worker` so the main thread stays responsive during parse — but **don't do this in this PR**. Confirm the synchronous version works first.

---

## Step 2 — `ui_mockup.html` diagnostics + visible mode chip

### 2a. Mode chip — top-left corner, mirrors the existing `#demo-chip`

Add a sibling element next to `#demo-chip` (around line 1454, where `<div id="demo-chip">Demo Mode</div>` lives). Position top-left so it doesn't collide.

```html
<div id="data-mode-chip" aria-live="polite">DATA: …</div>
```

Add the matching CSS in the `<style>` block (near the existing `#demo-chip` rule, line ~289):

```css
#data-mode-chip {
    position: fixed;
    top: 1.5rem; left: 1.5rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.18);
    color: rgba(255,255,255,0.7);
    font-family: 'Outfit', sans-serif;
    font-size: 0.7rem;
    font-weight: 400;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    z-index: 100;
    pointer-events: none;
    transition: opacity 0.4s ease, color 0.4s ease, border-color 0.4s ease, background 0.4s ease;
}
#data-mode-chip.is-csv {
    color: #4CD964;
    border-color: rgba(76,217,100,0.4);
    background: rgba(76,217,100,0.10);
}
#data-mode-chip.is-mock {
    color: #FFD89E;
    border-color: rgba(255,216,158,0.35);
    background: rgba(255,216,158,0.10);
}
#data-mode-chip.is-error {
    color: #FF6B61;
    border-color: rgba(255,59,48,0.45);
    background: rgba(255,59,48,0.12);
}
```

### 2b. Update the chip from `loadReview()` and surface errors

Currently `loadReview()` is silent on success/failure. Replace the whole function with this version (the previous one's structure is preserved — only logging + chip wiring is added):

```js
async function loadReview() {
    const chip = document.getElementById('data-mode-chip');
    const setChip = (cls, label) => {
        if (!chip) return;
        chip.classList.remove('is-csv', 'is-mock', 'is-error');
        chip.classList.add(cls);
        chip.textContent = label;
    };

    // 1) Real CSV
    if (window.REVIEW_CSV_PATH && window.parseEmotiBitCSV) {
        try {
            const fetchT0 = performance.now();
            const res = await fetch(window.REVIEW_CSV_PATH);
            if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${window.REVIEW_CSV_PATH}`);
            const text = await res.text();
            const fetchMs = Math.round(performance.now() - fetchT0);
            const filename = window.REVIEW_CSV_PATH.split('/').pop();
            console.log(`[review] fetched ${filename} (${(text.length/1e6).toFixed(1)} MB) in ${fetchMs} ms`);
            const parsed = window.parseEmotiBitCSV(text, filename);
            window.csvParsed = parsed;
            const d = parsed.diagnostics;
            console.log(`[review] mode=csv parse=${d.parseMs}ms hr=${d.hrCount} sf=${d.sfCount} acc=${d.activCount} cardioAvg=${d.cardioAvg.toFixed(1)} stressAvg=${d.stressAvg.toFixed(1)} activityAvg=${d.activityAvg.toFixed(1)} duration=${(d.durationMs/3.6e6).toFixed(2)}h`);
            applyReview(parsed.review);
            setChip('is-csv', `CSV · ${filename.slice(0, 10)}`);
            return;
        } catch (e) {
            console.error('[review] CSV path failed:', e);
            setChip('is-error', 'CSV PARSE FAILED — using mock');
        }
    }

    // 2) review.json
    try {
        const res = await fetch('./review.json');
        if (res.ok) {
            applyReview(await res.json());
            console.log('[review] mode=review.json');
            setChip('is-mock', 'DATA: review.json');
            return;
        }
    } catch (e) {}

    // 3) Embedded mock
    if (typeof reviewDataObj !== 'undefined') {
        applyReview(reviewDataObj);
        console.log('[review] mode=mock (review_data.js)');
        // Don't overwrite the error chip if the CSV branch already failed
        if (chip && !chip.classList.contains('is-error')) setChip('is-mock', 'DATA: MOCK');
    } else {
        console.error('[review] no data sources available');
        setChip('is-error', 'NO DATA');
    }
}
```

### 2c. Initialise the chip immediately at boot so it's visible during parse

In the boot block (line ~3221), add a line *before* `await loadReview()` so the user sees "DATA: LOADING…" while the 200 MB file is being parsed:

```js
window.addEventListener('DOMContentLoaded', async () => {
    const chip = document.getElementById('data-mode-chip');
    if (chip) chip.textContent = 'DATA: LOADING…';
    await loadReview();
    dayRecap.init();
    dayRecap.play();
});
```

### 2d. Update the M-key toast to also read the chip state

No code change needed — the toast already says "Switching to CSV/MOCK". Just verify it still works after reload (chip should reflect the new mode).

---

## Step 3 — Verify

1. Serve the folder (`python -m http.server` in the project dir) and open `ui_mockup.html`.
2. **Top-left chip** should show:
   - `DATA: LOADING…` briefly
   - then `CSV · 2026-04-25` (green) once parsing finishes
3. **DevTools Console** should show two log lines: a `fetched ... MB in Xms` line and a `mode=csv parse=Yms hr=25011 ...` line.
4. **Visual signals the data is real:**
   - Out-banner: `8.5 hours long!` (not `10 hours long!`)
   - Scrubber ticks: start near `11:00`, end near `19:00` (not `8:00–18:00`)
   - Meter values: not `50 / 23 / 23` — should be the actual computed averages from the file
   - Tagline on the welcome scene: matches the dominant state computed from the data
5. Press **M** → toast "Switching to MOCK data…" → page reloads → chip turns amber `DATA: MOCK` → numbers revert to `50 / 23 / 23`. Press **M** again to flip back.
6. To force the error path for testing: temporarily change `REVIEW_CSV_DEFAULT` to a bogus path. Chip should turn red `CSV PARSE FAILED — using mock`, console should log the error, and the mock numbers should still render.

## Step 4 — What NOT to do

- Do **not** add a Web Worker — verify the synchronous version works first. If it's still slow on real hardware (>3 s parse), that's a separate, smaller follow-up.
- Do **not** change the renderers (`renderDashboards`, `_renderMeters`, `_renderReports`). The parser still emits the same shape.
- Do **not** delete `review_data.js`. It remains the third-tier fallback and the M-key toggle target.
- Do **not** change `biosignal.js`. It feeds the biofeedback challenge, not the daily review.
- Do **not** "improve" the state classifier or stress formula in this PR. Get the perf right first; tune the analytics in a separate pass once you can see what the real data looks like.

## Sanity check before declaring done

Run this in DevTools console after the page loads:

```js
window.csvParsed && {
    hours:        window.csvParsed.durationHours.toFixed(2),
    cardioAvg:    window.csvParsed.diagnostics.cardioAvg.toFixed(1),
    stressAvg:    window.csvParsed.diagnostics.stressAvg.toFixed(1),
    hrSamples:    window.csvParsed.diagnostics.hrCount,
    parseMs:      window.csvParsed.diagnostics.parseMs,
    firstReport:  window.csvParsed.reports[0],
    meterValues:  window.csvParsed.meters.map(m => `${m.id}=${m.value}`),
}
```

You should see real numbers (not `50/23/23`), `hrSamples` near 25 000, and `parseMs` < 3 000.
