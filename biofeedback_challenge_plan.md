# Biofeedback Challenge — Implementation Plan (v2)

> Scope: redesign the `#scene-biofeedback` scene in `ui_mockup.html`.
> Revised after peer review (`peer_review.md`) and live-data confirmation
> from `C:\Program Files\EmotiBit\EmotiBit Oscilloscope\data\oscOutputSettings.xml`.

---

## 0. Changelog vs. v1

- **Metric:** RMSSD → **RSA (HR amplitude)**. EmotiBit Oscilloscope streams
  smoothed `HR` over OSC but no IBI/RMSSD channel, so RMSSD is not feasible
  for this hackathon. RSA is computable from the `HR` stream alone and is a
  legitimate vagal-tone proxy.
- **Win-hold:** 15s → **30s**. 15s was less than one 4-4-4-4 cycle and
  could be won on a single data spike.
- **Breathing pattern:** 4-4-4-4 box → **4-4-6-2 (variable-speed dot)**.
  Extended exhale is more parasympathetic-effective than equal holds.
  Dot speed varies per side; box geometry stays.
- **Center number:** removed entirely. The avatar is the focal point.
- **Numeric countdown:** demoted to a small, low-opacity number near the
  active side label. Optional. Dot position itself encodes "time left."
- **Modes/options:** none. One default for everything.
- **Stop button:** added at bottom of left column.
- **Data ingestion:** real path defined (OSC → Python WS bridge → browser).
  Mock still exists as a fallback profile.

---

## 1. Layout

Three-column vertical split filling the viewport.

```
┌────────────────┬────────────────────────────┬────────────────┐
│   TIP          │                            │                │
│   (rotating,   │   AVATAR + BOX-BREATH      │   HP BAR       │
│    top)        │   FRAME                    │   (RSA)        │
│                │                            │                │
│   …            │                            │                │
│                │                            │                │
│   STOP BTN     │                            │                │
│   (bottom)     │                            │                │
│   ~22% width   │   ~56% width               │   ~22% width   │
└────────────────┴────────────────────────────┴────────────────┘
```

CSS: `display: grid; grid-template-columns: 22fr 56fr 22fr;`. Left column
uses `justify-content: space-between` so the tip sits near the top and the
Stop button at the bottom. Min column width 240px; <900px viewport → stack
vertically with avatar first.

---

## 2. Right column — RSA HP bar

### 2.1 Metric — **RSA (HR amplitude)**

EmotiBit Oscilloscope OSC patchboard exposes `/EmotiBit/0/HR` (smoothed BPM).
No `IBI` or live RMSSD channel. RMSSD-based HRV would require custom PPG
beat-detection; out of scope for the hackathon.

**RSA (Respiratory Sinus Arrhythmia)** is the right substitute:
- During paced breathing, HR rises on inhale, falls on exhale.
- `RSA_amplitude = HR_peak_during_inhale − HR_trough_during_exhale`, computed
  per breath cycle.
- Average over the **last 2 cycles** (rolling) → the value the bar displays.
- This is a real vagal-tone proxy used in clinical literature, computable
  from a 1–2 Hz HR stream.

### 2.2 Goal (personal baseline)

- Capture a **60s pre-challenge baseline** of RSA amplitude while the user is
  on the review scene (passive collection — no prompt).
- Target: `baseline + 30%`, with a floor of **6 bpm absolute** (so that flat-
  baseline users — e.g. already calm — still have a meaningful goal).
- **Win condition: maintain RSA ≥ target for 30 continuous seconds**
  (~2 full breath cycles at the 16s default — enough to rule out artifacts).

### 2.3 Visual

- Vertical bar, ~80% column height, ~24px wide, rounded ends.
- Fill = `clamp((current − baseline) / (target − baseline), 0, 1.2)`.
- Color states (CSS var `--hp-color`):
  - `< 33%` → red `#FF3B30`
  - `33–66%` → amber `#FFD89E`
  - `66–<100%` → cyan `#4AC8FF`
  - `≥ 100%` → green `#4CD964` with **steady** outer glow (NOT pulsing — pulse
    competes with breath rhythm; addresses peer-review sensory-load concern)
- Above the bar: small label `RSA` with current value (`8.2 bpm swing`).
- Below the bar: dashed target marker line + tiny "target" label.
- During the 30s win-hold, a thin progress arc wraps the target marker
  filling clockwise. Resets if user drops below target.

### 2.4 Color/avatar coupling

Avatar tint is driven by **HP bar fill ratio**, NOT raw HR. Tween duration
**1.5–2s** (slow — felt, not seen; addresses sensory-load concern):
- bar < 33% → red shift
- bar 33–66% → neutral
- bar 66–<100% → cyan
- win → gold `#FFD89E`

---

## 3. Center column — avatar + box-breathing frame

### 3.1 Avatar

- Reuse `avatar.png` (already in repo). **The avatar stays the focal point —
  no number overlays in the center.**
- Position: dead center of column.
- Color: see §2.4.
- Scale tied to breath phase (see §3.4).

### 3.2 Box frame

- SVG square outlined around the avatar, side ~`min(60vh, 60vw)`.
- Stroke 3px, color = current `--hp-color`.
- A **dot** (filled circle, ~12px radius) traverses the perimeter via GSAP
  `MotionPathPlugin`. One full lap = one full breath cycle.
- Side labels outside the box:
  - Top    = "Inhale"
  - Right  = "Hold"
  - Bottom = "Exhale"
  - Left   = "Hold"
- Active side label: opacity 1.0, scale 1.05. Inactive: opacity 0.4. Tween
  600ms on phase change.

### 3.3 Phase timing — **4-4-6-2 with variable dot speed**

Single default. No user-facing toggles.

| Phase | Duration | Why |
|---|---|---|
| Inhale | 4s | Comfortable, non-strained |
| Hold (top) | 4s | Brief — preserves box metaphor without inducing air hunger |
| Exhale | 6s | **Extended exhale = strongest parasympathetic activator** (peer-review point 3.B) |
| Hold (bottom) | 2s | Minimal — acts as a beat before the next inhale |

Total cycle = 16s (matches the 4-4-4-4 cycle length, so timing math elsewhere
doesn't change). 5.6 breaths/min — close to resonance frequency.

**Variable dot speed** (key change from v1): the dot's speed along each side
is `side_length / phase_duration`. So the dot crawls slowly along the exhale
side (slowest = most calming), moves uniformly on the inhale, and glides
quickly through the holds. Geometry of the box stays a perfect square — only
the *temporal* pacing changes per side. This visually teaches the rhythm:
"the dot is slowest where the calm lives."

### 3.4 Avatar scale per phase

- Inhale (4s):       scale 0.94 → 1.12  (ease: `power2.out`)
- Hold-top (4s):     scale stays at 1.12
- Exhale (6s):       scale 1.12 → 0.94  (ease: `power2.inOut`)
- Hold-bottom (2s):  scale stays at 0.94

### 3.5 Numeric countdown — **peripheral, not central**

A small number (~1.2rem, font-weight 200, opacity 0.5, tabular-nums) sits
**just outside the box, adjacent to the active side's label**, showing
seconds left in the current phase. Moves with the active side.

Rationale: the user's eyes belong on the avatar. The dot already encodes
"time remaining" (its position along the side). The number is a peripheral
backup, not a focal element. **No big center countdown.**

### 3.6 State machine

```
phases = [
  { name: 'inhale',   duration: 4 },
  { name: 'hold_top', duration: 4 },
  { name: 'exhale',   duration: 6 },
  { name: 'hold_bot', duration: 2 },
]

on phase enter:
  - GSAP tween dot along the side (duration = phase.duration, ease: 'none')
  - GSAP tween avatar scale to phase target
  - reassign 'active-side' class + reposition peripheral countdown
  - start a 1-Hz secondsLeft ticker that updates the peripheral number

on phase complete:
  - advance index (wrap mod 4)
```

---

## 4. Left column — Tip panel + Stop button

### 4.1 Tip panel (top portion)

- Rotates every **20 seconds** (revised from 10s — reading is cognitive load,
  slower rotation reduces it; addresses peer-review sensory-load concern).
- One tip at a time, Fraunces italic, `clamp(1rem, 2vw, 1.4rem)`,
  `--fg-muted` color.
- 600ms crossfade.
- Source: `tips.js` — array of ~20 entries, each tagged for future
  context-aware selection.

```js
{ text: "Soften your jaw.", tag: "somatic", suits: ["high-hr", "anytime"] }
```

v1 picks randomly. v2 (later) will filter by `suits` based on live state.

**Tip content rules:** 6–10 words; present-tense; sensory/somatic; no
cognitive demands; no medical claims.

### 4.2 Stop button (bottom of left column)

- Glass-style button (matches existing `button` styles in `ui_mockup.html`),
  text "Stop". Sits at the bottom of the left column.
- On click:
  - Kill all running GSAP tweens (dot, avatar, bar, ticker).
  - Soft outro: avatar fades to neutral cyan, scene crossfades back to the
    review scene (`#scene-review`).
  - **No "are you sure?" modal** — stopping is a calming gesture, not a
    destructive one. Friction here would be hostile.
- Accessibility: `aria-label="Stop biofeedback challenge"`, min-height 48px,
  focus ring already covered by existing `button:focus-visible`.

---

## 5. Win / loss / stop flow

| Outcome | Trigger | Behavior |
|---|---|---|
| **Win** | RSA ≥ target held 30s | Avatar → gold, bar locks at full with steady glow, box stroke → gold, run existing `triggerBloom()` |
| **Timeout** | 3 min elapsed without win | Soft message "You showed up. That counts." → bloom outro with muted gold |
| **Stop** | User clicks Stop | Crossfade back to `#scene-review`. No outro, no judgement. |

All three log the same telemetry (final RSA, duration, peak amplitude).

---

## 6. Data ingestion — EmotiBit live path

### 6.1 The chain

```
EmotiBit hardware
    │
    ▼  Bluetooth/USB
EmotiBit Oscilloscope.exe
    │   (config: data/oscOutputSettings.xml)
    │   sends OSC messages to localhost:12345
    ▼
Python WebSocket bridge  ← NEW (small script)
    │   listens on UDP :12345 for /EmotiBit/0/HR
    │   re-emits as JSON over WS :8765
    ▼
ui_mockup.html (browser)
    │   biosignal.js subscribes to ws://localhost:8765
    ▼
RSA computation (in-browser, JS)
    │   buffers HR samples per breath phase, computes peak−trough
    ▼
HP bar + avatar tint
```

### 6.2 Why a bridge is needed

Browsers cannot read raw OSC/UDP. The bridge is ~30 lines of Python using
`python-osc` + `websockets`. It can live in `emomirror/osc_to_ws_bridge.py`
alongside the existing `emomirror/osc_bridge.py` (which is the *outbound*
TouchDesigner bridge — different direction).

### 6.3 `biosignal.js` interface

```js
// Hardware-agnostic — ui_mockup.html only depends on this contract
const biosignalSource = {
  subscribe(cb) { /* cb({ hr, timestamp }) called at ~1–2 Hz */ },
  unsubscribe(cb),
  setMode('live' | 'mock'),
  setMockProfile('success' | 'struggle' | 'realistic'),
};
```

If the WS connection fails, fall back to mock automatically and log a warning
(no error UI — the mock is good enough for demo).

### 6.4 RSA computation (browser-side)

```
buffer = ring buffer of last ~20s of (hr, timestamp) samples
on each new sample:
  if current phase === 'inhale':
    track max HR seen this phase
  if current phase === 'exhale':
    track min HR seen this phase
  on phase transition inhale→hold or exhale→hold:
    record (peak, trough) pair
  every cycle complete:
    rsa = mean of last 2 cycles' (peak − trough)
    push to HP bar
```

Smooth with a small EMA (α ≈ 0.4) to reduce jitter on the bar.

---

## 7. Files to touch

| File | Change |
|---|---|
| `ui_mockup.html` | Replace `#scene-biofeedback` markup with the 3-col layout. Add box-frame SVG, dot path, HP bar SVG, tip panel, Stop button. Update CSS for grid + new state classes. Refactor `startBiofeedback()` / `onProgressUpdate()` / `triggerBloom()` to consume the phase state machine and RSA stream. Slow avatar color tweens to 1.5–2s. Remove the giant center countdown. |
| `tips.js` *(new)* | ~20 tagged tips. |
| `biosignal.js` *(new)* | Live WS + mock subscriber (see §6.3). |
| `emomirror/osc_to_ws_bridge.py` *(new)* | UDP/OSC `:12345` → WS `:8765`, single channel `/EmotiBit/0/HR`. |
| `review_data.js` | Untouched. |

---

## 8. Open items (resolved)

1. ~~EmotiBit data path~~ → resolved. OSC on `localhost:12345`. Bridge to WS in §6.
2. ~~Win-hold duration~~ → resolved. 30s (peer review concession).
3. ~~Pause/abort mid-session~~ → resolved. Stop button bottom-left.
4. ~~Settings toggle for breathing pattern~~ → resolved. No options. Single default 4-4-6-2.

---

## 9. Out of scope

- Persisting challenge results to history (`review.json` does not consume
  challenge outcomes yet).
- Multi-session progression / streaks.
- Audio cues (gentle bell on phase change — nice-to-have).
- Context-aware tip selection (v2 — needs live state).
- Daily-adaptive tips from review.json (v3).
- Custom PPG beat-detection for true RMSSD (would require reading the
  `/EmotiBit/0/PPG:GRN` raw stream and running a peak detector — significant
  work, deferred until post-hackathon).
