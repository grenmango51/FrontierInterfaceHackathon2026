// csv_parser.js — streaming EmotiBit CSV parser
// Two-pass byte-level scan: never materialises per-sample objects.
// Public: window.parseEmotiBitCSV(text, filename) → { review, reports, meters, startDate, endDate, durationHours }

const userBaseline = {
    KEY: 'emomirror_baseline_v1',
    load() {
        try {
            const raw = localStorage.getItem(this.KEY);
            return raw ? JSON.parse(raw) : null;
        } catch(e) { return null; }
    },
    update(cardioAvg, stressAvg) {
        let b = this.load() || { 
            cardio: { mean: 0, m2: 0, n: 0, std: 0 }, 
            stress: { mean: 0, m2: 0, n: 0, std: 0 } 
        };
        
        const updateMetric = (val, stats) => {
            stats.n = Math.min(stats.n + 1, 30); // rolling 30-session window
            const delta = val - stats.mean;
            stats.mean += delta / stats.n;
            const delta2 = val - stats.mean;
            stats.m2 += delta * delta2;
            stats.std = stats.n > 1 ? Math.sqrt(stats.m2 / (stats.n - 1)) : 0;
        };

        updateMetric(cardioAvg, b.cardio);
        updateMetric(stressAvg, b.stress);
        localStorage.setItem(this.KEY, JSON.stringify(b));
    }
};

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
                    const tag = text.substring(tagStart, tagEnd).trim(); // trim in case of whitespace
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

    // ── State classification (relative to user baseline) ─────────────────
    function classifyState(cardio, stress, activity, baseline) {
        if (cardio == null) return 'calm';
        
        // Cold-start fallback if we don't have enough history
        if (!baseline || baseline.cardio.n < 3 || baseline.cardio.std < 1) {
            if (stress > 60 && cardio > 60) return 'overstimulated';
            if (stress > 45) return 'anxious';
            if (cardio > 60 && activity > 40) return 'active';
            if (cardio > 55) return 'stressed';
            if (cardio < 40 && activity < 15) return 'fatigued';
            return 'calm';
        }

        const c = baseline.cardio;
        const s = baseline.stress;

        // Sigma-based thresholds (anchored to user's personal normal)
        const isStressedHigh = cardio > (c.mean + c.std * 1.5);
        const isStressHigh   = stress > (s.mean + s.std * 1.5);
        const isStressed     = cardio > (c.mean + c.std);
        const isAnxious      = stress > (s.mean + s.std);

        if (isStressHigh && isStressedHigh) return 'overstimulated';
        if (isAnxious) return 'anxious';
        if (isStressed && activity > 40) return 'active';
        if (isStressed) return 'stressed';
        if (cardio < (c.mean - c.std) && activity < 15) return 'fatigued';
        
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

    function buildReports(cardio30, stress30, activity30, baseline) {
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
            const state = classifyState(c.v, s, a, baseline);
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
        const baseline = userBaseline.load();
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
                // SF is inter-beat interval in seconds. Range [0.3, 3.0] covers HR 20-200.
                forEachValue(txt, vS, vE, v => {
                    if (v < 0.3 || v > 3.0) return;
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
        });

        // SF post-pass: now we know min/max, fold into stress aggregates.
        // Using a robust range (10th to 90th percentile) to avoid "flat lines" caused by sensor noise.
        if (sfRaw.length > 20) {
            const sortedVals = sfRaw.map(s => s.v).sort((a, b) => a - b);
            const p10 = sortedVals[Math.floor(sortedVals.length * 0.10)];
            const p90 = sortedVals[Math.floor(sortedVals.length * 0.90)];
            const range = (p90 - p10) || 1;
            
            for (let i = 0; i < sfRaw.length; i++) {
                const s = sfRaw[i];
                // Clamp to [0, 100] after robust normalization
                const stressScore = Math.max(0, Math.min(100, ((s.v - p10) / range) * 100));
                stressB5.add(s.tMs, stressScore);
                stressB30.add(s.tMs, stressScore);
            }
        } else if (sfRaw.length) {
            // Fallback for very short recordings
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

        const dominantState = classifyState(cardioAvg, stressAvg, activityAvg, baseline);
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

        const reports = buildReports(cardio30, stress30, activ30, baseline);
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
            diagnostics: {
                parseMs:    Math.round(parseMs),
                hrCount:    cardioStats.count,
                sfCount:    sfRaw.length,
                activCount: activStats.count,
                cardioAvg, stressAvg, activityAvg,
                durationMs,
                baseline: baseline ? { n: baseline.cardio.n } : null,
            },
        };
        
        // Persist session to rolling baseline
        userBaseline.update(cardioAvg, stressAvg);

        return result;
    };

})();
