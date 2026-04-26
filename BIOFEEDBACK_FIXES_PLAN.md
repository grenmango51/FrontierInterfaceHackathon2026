# Biofeedback Fixes — Execution Plan

Scope: four targeted changes to the biofeedback pipeline. Item 5 from the audit (adaptive target / calibration window) is **out of scope** for this plan and is being designed separately. Do not touch the auto-gain logic in `ui_mockup.html` lines 2038–2045.

Read [BIOFEEDBACK_AUDIT.md](BIOFEEDBACK_AUDIT.md) for context on what was originally changed and why. The verdict on each item below is the result of a follow-up review against the raw CSV data.

---

## Change 1 — Simplify HR smoothing in `biosignal.js`

**File**: [biosignal.js:73-85](biosignal.js#L73-L85)

**Current behavior**: Maintains `_ibiHistory` (last 3 IBIs), emits HR as `60000 / mean(_ibiHistory)`.

**Target behavior**: Emit HR from the raw IBI, with a median-of-3 guard against single-IBI spikes.

**Why**: The downstream RSA computation in `ui_mockup.html` (`_recordCycle`, lines 2000–2020) already uses p75/p25 of all samples in a phase, which is inherently outlier-robust. The mean-of-3 in `biosignal.js` is double-smoothing — it adds ~1.5 beats of lag and bleeds samples across phase boundaries, biasing the percentile computation.

**Implementation**:
1. Keep `_ibiHistory` as a ring of the last 3 IBIs (used only for the median guard, not for averaging).
2. On each new beat: push the IBI, then compute `medianIbi = median(_ibiHistory)`. If the new IBI differs from the median by more than 30%, emit HR from the median; otherwise emit HR from the raw new IBI.
3. Remove the `60000 / avgIbi` averaging line. Replace with the conditional above.
4. Update the inline comment on line 80 to explain that smoothing is now downstream's responsibility and this layer only guards against single-IBI dropouts.

**Verification**:
- Mock mode (`success` profile) should still produce a clean HR curve — the median guard rarely fires on synthetic data.
- In live mode, log when the median guard rejects a value. Expect <5% rejection rate on a clean session.

---

## Change 2 — Tighten SF percentile normalization in `csv_parser.js`

**File**: [csv_parser.js:277-325](csv_parser.js#L277-L325)

**Current behavior**: Pass 2 collects every SF sample into `sfRaw[]`. After parsing, sorts the array, takes p05/p95 as the normalization range.

**Target behavior**: Add a hard physical clip during ingest, widen the percentile band to 10/90, keep the existing post-pass structure.

**Why**: SF is an inter-beat interval in seconds. Values outside ~[0.3, 3.0] s correspond to HR < 20 bpm or > 200 bpm and are physically impossible for the use case. Dropping them at ingest is cleaner than relying on percentile clipping alone, and 10/90 is more forgiving when contamination exceeds 5%.

**Implementation**:
1. In the `tag === 'SF'` branch (line 277), before pushing to `sfRaw`, drop samples where `v < 0.3 || v > 3.0`. Do not update `sfMin`/`sfMax` for dropped samples.
2. In the post-pass (line 305–306), change percentiles from `0.05` / `0.95` to `0.10` / `0.90`.
3. Leave the `< 20 samples` fallback branch (line 316) untouched.
4. Add a one-line comment above the SF branch explaining the physical bounds.

**Do not** refactor `sfRaw` to a streaming P² estimator. The current implementation is fine for session lengths we care about; that refactor is its own ticket.

**Verification**:
- Run the parser against `2026-04-24_21-29-04-581986.csv`. Compare the resulting `stress_avg` value before and after — it should change modestly (a few percent), not drastically. A drastic change means the clip is too aggressive.
- Check that `sfRaw.length` after ingest is not catastrophically smaller than before (expect <2% drop on real data).

---

## Change 3 — Replace hardcoded state thresholds with per-user baselines

**File**: [csv_parser.js:112-121](csv_parser.js#L112-L121) and the `parseEmotiBitCSV` entry point

**Current behavior**: `classifyState` uses hardcoded thresholds (e.g., `stress > 60`, `cardio > 55`). Same numbers for every user, every session.

**Target behavior**: Thresholds are computed from a rolling per-user baseline (mean and standard deviation of recent sessions), persisted in `localStorage`. States are defined relative to that baseline (e.g., "stressed = cardio > userMean + 1σ").

**Why**: The current thresholds are calibration-by-vibes. Different users will have different resting cardio/stress distributions; the same number can't fit all of them. Anchoring to the user's own history makes states meaningful as deviations from *their* normal.

**Implementation**:
1. Add a baseline store module (top of `csv_parser.js`, before the IIFE):
   ```
   userBaseline: {
     load() — read from localStorage key `emomirror_baseline_v1`. Returns
       { cardio: {mean, std, n}, stress: {mean, std, n} } or null if not set.
     update(cardioAvg, stressAvg) — incrementally update mean/std using
       Welford's algorithm. Cap n at 30 sessions (rolling window via
       n = min(n+1, 30)). Persist to localStorage.
   }
   ```
2. Modify `classifyState` to take a fourth argument `baseline`. Threshold logic:
   - If `baseline === null` or `baseline.cardio.n < 3`: fall back to current hardcoded thresholds (cold-start).
   - Otherwise, define `stressed`, `anxious`, `overstimulated`, `fatigued` as σ-offsets from the user's mean. Suggested mapping:
     - `overstimulated`: stress > μ+1.5σ AND cardio > μ+1.5σ
     - `anxious`: stress > μ+1σ
     - `stressed`: cardio > μ+1σ
     - `fatigued`: cardio < μ−1σ AND activity < 15
     - `active`: cardio > μ+0.5σ AND activity > 40
     - `calm`: otherwise
3. In `parseEmotiBitCSV` (line 203), call `userBaseline.load()` once at entry. Pass the baseline into `classifyState` (and into `buildReports`, which calls `classifyState` per row — line 183).
4. After the parse completes (line 391), call `userBaseline.update(cardioAvg, stressAvg)` to incorporate the new session.
5. Add `baseline` to the returned `diagnostics` object (line 402) so the UI can display "based on N sessions" if desired.

**Verification**:
- First-ever session: should behave exactly like the current implementation (cold-start fallback).
- After 3+ sessions: classifications should shift to be relative. Test by running the same CSV twice in a row and confirming `localStorage` updates.
- Clear `localStorage.emomirror_baseline_v1` between test runs.

---

## Change 4 — Remove redundant per-sample HR outlier filter

**File**: [ui_mockup.html:1974-1998](ui_mockup.html#L1974-L1998)

**Current behavior**: `_onNewHR` rejects any sample where `|hr - _lastHR| > 15` bpm, with a glitch animation side-effect.

**Target behavior**: Remove the rejection branch. Keep the glitch hook but trigger it from a different signal source.

**Why**: This filter is redundant with the cycle-level percentile rejection at lines 2007–2015 (which is more principled — it rejects an entire bad cycle rather than picking off individual samples). Stacking both creates a stateful trap: when several samples are rejected in a row, `_lastHR` becomes stale and good samples start looking like jumps.

**Implementation**:
1. Delete lines 1977–1988 (the entire outlier rejection block including the glitch animation).
2. The function body becomes simply: update `_lastHR`, then route the sample to `_inhaleHRs` or `_exhaleHRs` based on phase.
3. Move the glitch trigger to the cycle-rejection path at line 2014. When `_recordCycle` rejects a cycle (the `else` branch logging "Rejected cycle"), fire the same glitch animation that used to be at lines 1983–1985.
4. Leave Change 1's median guard in `biosignal.js` to handle single-sample noise upstream.

**Verification**:
- Run the breathing challenge in mock mode with `realistic` profile. The bar should fill smoothly; no behavioral change is expected because mock data has no >15 bpm jumps.
- In live mode with noisy hardware, expect the avatar to glitch *less often* (only on bad cycles, not bad samples) but more meaningfully.

---

## Order of execution

Changes are independent except that **Change 1 should land before Change 4** — Change 4 removes the per-sample safety net, and Change 1's median guard in `biosignal.js` is what replaces it. If you reverse the order, there's a brief window where noisy live data can pollute cycle aggregates.

Suggested order: **1 → 4 → 2 → 3**.

---

## Out of scope

- Item 5 from the original audit (adaptive auto-gain target). Leave [ui_mockup.html:2038-2045](ui_mockup.html#L2038-L2045) untouched. A separate plan will replace it with a calibration-window approach.
- Streaming P² quantile estimator for `sfRaw`.
- Signal Quality Index from accelerometer magnitude.
- Any changes to mock profiles or breathing phase durations.
