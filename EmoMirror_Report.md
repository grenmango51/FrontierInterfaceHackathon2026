# EmoMirror — System Report

> *An interactive biosignal art installation that transforms your physiology into a living mirror of your emotional self.*

---

## 1. What Is EmoMirror?

EmoMirror is a full-stack biosensing installation built for the **FrontierInterface Hackathon 2026** at Aalto University, track: *Storytelling with Biosensing in TouchDesigner*.

It reads a full day of physiological data from an **EmotiBit wearable sensor**, infers the wearer's emotional state using a machine learning engine, and reflects that state back through a **generative holographic avatar** on a two-way mirror display. When the user chooses to engage, they enter a real-time **biofeedback challenge** — where they win not by pressing buttons, but by bringing their own body back to calm.

---

## 2. The Core Idea

> *Your body has been telling a story all day. EmoMirror shows it back to you — and gives you a way to rewrite the ending.*

The system has three acts:

| Act | What happens |
|-----|-------------|
| **The Mirror Awakens** | User arrives home. The installation auto-discovers the EmotiBit on the local network, downloads the day's data via FTP, processes it through the ML pipeline, and the mirror glows to life with an avatar shaped by the day's emotional arc. |
| **The Day Review** | A cinematic dashboard reflects the day's cardiovascular load and stress levels — with highlights, adaptive questions, and a timeline of emotional moments that invite reflection. |
| **The Biofeedback Challenge** | The user presses "Restore Balance." Guided by box-breathing for up to 3 minutes, their live physiology drives the avatar through Storm → Focus → Blooming as their body calms. |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMOMIRROR — FULL PIPELINE                    │
└─────────────────────────────────────────────────────────────────┘

  [EmotiBit Wearable]
        │  Worn all day — records HR, EDA, PPG, motion, temperature to SD card
        │  Simultaneously streams live OSC to EmotiBit Oscilloscope (WiFi)
        ↓
  [emotibit_auto/ — Python]
        │  discover.py     — Threaded subnet scan (64 workers) + FTP auth → finds device IP
        │  transfer.py     — FTP downloads raw .csv + _info.json (skips duplicates)
        │  parse.py        — Runs EmotiBit DataParser .exe → per-TypeTag .csv files
        │  watcher.py      — Main loop (every 30s): discover → transfer → parse → hook
        ↓
  [emomirror/hook.py — Python]
        │  Entry point called by watcher after parse completes
        │  Orchestrates: features → ML → insights → OSC → mode transition
        ↓
  [emomirror/features.py]
        │  Reads per-TypeTag CSVs → extracts hr_mean, eda_mean, activity_mean, temp_mean
        ↓
  [emomirror/ml_engine.py]
        │  Loads personal baseline (user_baseline.json) or falls back to population defaults
        │  Computes σ-deviations per feature → rule-based state classification
        │  Returns: (state_name, intensity 0–1, deviations dict)
        ↓
  [emomirror/scoring.py + review_engine.py]
        │  scoring.py       — Cardio Load & Stress scores (0–100) per 5-min epoch
        │  review_engine.py — Highlight detection, question selection, daily summary JSON
        ↓
  [emomirror/osc_bridge.py]
        │  Sends state, color, intensity, glitch, HR, EDA, insight to TouchDesigner
        │  OSC/UDP → localhost:7400
        ↓
  [TouchDesigner — EmoMirror.toe]        ← Architecture defined; .toe not yet built
        │  OSC In CHOP → State Machine (Python DAT)
        │  Generative avatar: particles, GLSL shaders, noise distortion
        │  Two-way mirror display: pure black background required

  ─── PARALLEL: LIVE STREAM PATH (Biofeedback) ───────────────────

  [EmotiBit Oscilloscope]
        │  Streams live HR + PPG:GRN → OSC localhost:12345
        ↓
  [emomirror/osc_to_ws_bridge.py]
        │  Bridges OSC :12345 → WebSocket :8765 (JSON broadcast to browser)
        ↓
  [biosignal.js — Browser]
        │  Adaptive PPG peak detector (25 Hz green channel)
        │  Rolling IBI → instantaneous HR → RSA amplitude calculation
        │  Falls back to mock profile if WebSocket unavailable
        ↓
  [ui_mockup.html — Challenge Engine]
        │  Box breathing: 4s inhale / 4s hold / 6s exhale / 2s hold
        │  RSA meter: fills as HR amplitude rises toward target
        │  Win: RSA ≥ target for 30 continuous seconds
        ↓
  [emomirror/biofeedback.py — Python]  ← Parallel Python path for TouchDesigner
        │  Also listens on OSC :12345 (same live stream)
        │  Computes progress → sends /emo/biofeedback/progress to TouchDesigner
```

---

## 4. The Sensors — What EmotiBit Measures

EmotiBit is an ESP32 Feather Huzzah FeatherWing stack with the following sensors:

| Signal | TypeTag | Rate | What it reveals |
|--------|---------|------|-----------------|
| Heart Rate (derived) | HR | ~1 Hz | Arousal, exertion, stress |
| EDA — skin conductance | EA | 15 Hz | Emotional arousal, stress response |
| Electrodermal Level | EL | 15 Hz | Tonic baseline conductance |
| Electrodermal Response | ER | 15 Hz | Phasic sweat response |
| PPG Infrared | PI | 25 Hz | Deep blood volume pulse |
| PPG Red | PR | 25 Hz | Tissue oxygenation |
| PPG Green | PG | 25 Hz | Surface pulse (used for peak detection) |
| SCR Amplitude | SA | event | Sweat spike intensity |
| SCR Frequency | SF | event | Sweat events per minute |
| SCR Rise Time | SR | event | Time to peak sweat |
| Accelerometer 3-axis | AX/AY/AZ | 25 Hz | Physical activity, movement |
| Gyroscope 3-axis | GX/GY/GZ | 25 Hz | Rotation, gesture intensity |
| Magnetometer 3-axis | MX/MY/MZ | 25 Hz | Orientation (compass) |
| Skin Temperature | T1 / TH | 7.5 Hz | Peripheral blood flow, thermal state |

Raw data is stored as a single interleaved CSV on the SD card. EmotiBit DataParser splits it into individual per-TypeTag CSVs for processing.

---

## 5. Emotional State Classification

The ML engine (`ml_engine.py`) compares each session's biosignals to the user's **personal adaptive baseline**. Deviations are measured in standard deviation (σ) units.

### The 6 States

| State | Color | Detection Rule |
|-------|-------|----------------|
| 😌 **Calm** | Deep teal / blue | HR and EDA within ±0.5σ of baseline |
| 😟 **Anxious** | Yellow-orange | HR > +1σ AND EDA > +1σ AND low movement |
| 😰 **Stressed** | Orange / amber | HR > +1.5σ AND EDA > +1.5σ |
| 🏃 **Active** | Bright cyan / green | Activity > baseline AND HR > +1.5σ |
| 😴 **Fatigued** | Muted purple / grey | HR < −0.5σ AND near-zero movement |
| 🤯 **Overstimulated** | Red / hot pink | HR > +2σ AND EDA > +2σ |

### Adaptive Baseline

Personal baselines are computed by `calculate_baseline.py` from historical parsed CSVs and stored as `user_baseline.json`:

```json
{
  "hr_mean": 67.62,  "hr_std": 10.20,
  "eda_mean": 1.77,  "eda_std": 0.50,
  "activity_mean": 0.151,
  "temp_mean": 33.00,
  "cardio_mean": 45, "cardio_std": 10,
  "stress_mean": 40, "stress_std": 12,
  "peak_day": {
    "cardio": {"value": 49.45, "date": "2026-04-20"},
    "stress": {"value": 23.45, "date": "2026-04-22"}
  }
}
```

- **Day 1:** Population average defaults (HR ≈ 70 BPM, EDA ≈ 2 µS)
- **Day 2+:** Personal baseline computed from real recorded data
- **7 days of history** already stored in `data/demo_user/history/` (288 epochs/day × 7 days)

---

## 6. Scoring Engine

`scoring.py` computes two composite scores (0–100) for every 5-minute epoch:

### Cardiovascular Load
Reflects physical and cardiac exertion:
```
Cardio Score = 0.5 × HR_percentile + 0.3 × HR_std_percentile + 0.2 × Motion_percentile
```

### Stress Score
Reflects emotional/physiological stress — **only counted during low-motion periods** (motion gate ≤ 0.3) to avoid exercise sweat masquerading as stress:
```
Stress Score = 0.5 × SCR_freq_percentile + 0.3 × EDA_tonic_percentile + 0.2 × Temp_drop_bonus
```

SCR (skin conductance response) events are detected via a peak-finding algorithm on the EDA signal: rolling baseline subtraction, 0.05 µS threshold, 1-second minimum inter-peak gap.

All percentiles are computed relative to the user's personal baseline using: `(z_score + 3) / 6 × 100`, clamped to 0–100.

---

## 7. The Daily Review Dashboard

After the mirror awakens, a cinematic dashboard shows the full emotional arc of the day.

### Left Panel — Metrics

Two metrics tracked across 24 hours (288 × 5-min epochs):

- **Cardiovascular Load** — shown as a 24-hour sparkline with a 30-min moving average smoothing, baseline dashed line, and peak highlights
- **Stress Score** — same format; only meaningful during sedentary periods

Each metric has:
- A radial gauge filling from 0 to today's score vs. personal peak
- A delta chip: today vs. 7-day baseline (e.g., *"+13% vs your week"*)

### Highlight Detection

`review_engine.py` automatically finds the most significant moments in the day:

1. Compute scores per 5-min epoch
2. Smooth with 30-min moving average (6-epoch window)
3. Find contiguous runs where score > mean + 1.5σ
4. Keep only segments ≥ 15 minutes
5. Return top 2 per metric with start/end times and % above normal

### Right Panel — Adaptive Questions

3 questions are selected from a bank of 25+ templates by `review_engine.py`. Each question has:
- A **category** (anomaly_probe, pattern_reinforce, state_callout, recovery_probe, open_reflection)
- **Triggers** that bind it to detected highlights (e.g., times, percentages, activity guesses)
- A **priority score** and **cooldown** (won't repeat within N days)
- **Specificity weight** — more specific questions rank higher when their triggers fire

Selection scoring: `fit = match_strength × (0.6 + 0.4 × specificity) × priority`

Example generated question:
> *"Your stress peaked between 14:15 and 14:50 — 50% above your norm. What was happening?"*

User answers by typing or voice. Answers are stored and fed into the **activity memory** system.

---

## 8. The Day Recap Scene

A cinematic scroll through the day's emotional journey.

**Three-column layout:**

- **Left:** Three live meters (HR, EDA, motion) with radial gauges and delta chips vs. weekly baseline
- **Center:** A 6-state body visualization — a human silhouette that shifts state with per-state CSS animations:
  - Calm: slow breathing pulse
  - Stressed: rapid micro-jitter
  - Anxious: trembling
  - Active: energetic pulse
  - Fatigued: slow drooping
  - Overstimulated: violent shake
  - Each state has a matching aura color layer (radial gradient)
- **Right:** Vertical timeline scrubber (the day as a scroll). Report cards for each significant moment — each with a time, state label, description, and a reflective question. Users can reply to any card; replies are saved locally.

---

## 9. The Biofeedback Challenge

The centrepiece of the installation. Triggered by the user pressing **"Restore Balance."**

### How It Works

The user is guided through **box breathing** (4s inhale → 4s hold → 6s exhale → 2s hold) while the avatar and the room respond to their actual physiology in real time.

**The key metric is RSA (Respiratory Sinus Arrhythmia):** the natural oscillation in heart rate driven by breathing. During inhalation HR rises; during exhalation it drops. A larger swing signals stronger parasympathetic (calming) activation. The target swing is `baseline HR + 30%` (floor: 6 BPM).

### Progress Formula (browser, `biosignal.js` + challenge engine)

```
HR progress     = 1 − clamp(|current_HR − baseline_HR| / (2 × HR_std), 0, 1)
EDA progress    = 1 − clamp(|current_EDA − baseline_EDA| / (2 × EDA_std), 0, 1)
Motion progress = 1 − clamp(motion_level, 0, 1)
Overall         = 0.4 × HR + 0.4 × EDA + 0.2 × Motion
```

The same progress value is also sent to TouchDesigner as `/emo/biofeedback/progress` via `biofeedback.py`.

### The Three Visual Phases

| Phase | Progress | Avatar | Particles |
|-------|---------|--------|-----------|
| **The Storm** | 0–10% | Asymmetric, fragmented | Chaotic, red/orange, high turbulence |
| **The Focus** | 10–90% | Gradually stabilizing | Speed and turbulence decreasing |
| **The Blooming** | >90% | Perfectly symmetric, radiant | Teal/blue, expanding orbital aura |

### Win Condition
RSA ≥ target sustained for **30 continuous seconds** → victory (*"You've returned to your baseline. Carry this calm with you."*)

If not achieved within 3 minutes → compassionate conclusion (*"You showed up. That's enough."*)

### Real-Time Guidance

`biofeedback.py` (Python backend) generates dynamic instructions based on live HR/EDA trends:

| Condition | Instruction sent |
|-----------|-----------------|
| HR not dropping | *"Breathe slowly..."* |
| Motion too high | *"Soften your posture. Sit completely still."* |
| EDA dropping | *"You are doing great. Keep letting go."* |
| All metrics near baseline | *"Perfect. Hold this calm state."* |

The browser also rotates **somatic tips** (from `tips.js`) every 20 seconds — 20 body-focused prompts such as *"Soften your jaw"*, *"Let your shoulders drop"*.

---

## 10. The Avatar — Two-Way Mirror Design

The generative avatar is displayed behind a **two-way mirror**. This imposes one hard constraint:

> **All backgrounds must be pure black (`#000000`).** Black pixels are transparent (show the reflection). Colored pixels shine through the glass.

The avatar is an abstract human-form driven by:
- **Particle systems** — density, speed, and color driven by state intensity
- **Noise-distorted geometry** — glitch factor proportional to stress deviation
- **GLSL color shaders** — RGB per state sent over OSC
- **Feedback trails** — scaled to motion level
- **Text overlays** — insights and live metrics

### State → Visual Mapping

| State | Color | Form | Animation |
|-------|-------|------|-----------|
| Calm | Deep blue / teal | Smooth, symmetrical | Gentle breathing |
| Anxious | Yellow-orange | Warped, asymmetric | Trembling |
| Stressed | Orange / amber | Glitched, fragmented | Fast, jittery |
| Active | Bright green / cyan | Sharp, defined | Energetic pulses |
| Fatigued | Muted purple / grey | Melting, drooping | Very slow |
| Overstimulated | Red / hot pink | Heavily glitched | Strobing |

---

## 11. OSC Protocol — Python to TouchDesigner

All data is sent over OSC/UDP to `localhost:7400` by `osc_bridge.py`.

| Address | Type | Description |
|---------|------|-------------|
| `/emo/mode` | string | `idle` / `awakening` / `playback` / `realtime` / `biofeedback` |
| `/emo/state/current` | string | State name |
| `/emo/state/color/r,g,b` | float | RGB (0–1) per state |
| `/emo/state/intensity` | float | 0–1 |
| `/emo/state/glitch` | float | 0–1 distortion level (stress/overstim → higher) |
| `/emo/hr/current` | float | BPM |
| `/emo/hr/baseline` | float | Personal baseline BPM |
| `/emo/hr/deviation` | float | σ deviation |
| `/emo/eda/current` | float | µS |
| `/emo/eda/baseline` | float | Personal baseline EDA |
| `/emo/eda/deviation` | float | σ deviation |
| `/emo/motion/level` | float | Activity variance |
| `/emo/temp/current` | float | °C |
| `/emo/insight` | string | Natural language insight text |
| `/emo/timeline/progress` | float | 0–1 day playback position |
| `/emo/biofeedback/active` | int | 0 or 1 |
| `/emo/biofeedback/progress` | float | 0–1 |
| `/emo/biofeedback/scene` | string | `storm` / `focus` / `bloom` |

---

## 12. Activity Memory System

`activity_memory.py` learns what the user was doing during physiological peaks.

When the user answers a reflective question, the text is parsed for activity keywords (run, jog, yoga, meeting, presentation, meditation, etc.) and stored as a **normalized 5-dimensional signature vector**:

```
[hr_mean/150, hr_std/30, scr_freq/10, activity_mean/1, duration_min/120]
```

When future sessions show a similar physiological pattern, `match_signature()` uses **cosine similarity** to recall what activity was likely happening — personalizing the questions and insights over time.

---

## 13. Technology Stack

| Layer | Technology |
|-------|------------|
| **Wearable Hardware** | EmotiBit (ESP32 Feather Huzzah) — HR, EDA, PPG, IMU, Temp |
| **Data Acquisition** | Python — FTP auto-discovery + transfer + EmotiBit DataParser |
| **Signal Processing** | Python — NeuroKit2, HeartPy, SciPy, Pandas, NumPy |
| **State Inference** | Python — scikit-learn, rule-based ML engine, joblib |
| **OSC Bridge (Python→TD)** | Python — python-osc, port 7400 |
| **OSC Bridge (Oscilloscope→Browser)** | Python — python-osc + asyncio websockets, port 8765 |
| **Frontend** | HTML + GSAP 3.12.5 + Canvas API (single file, no build step) |
| **Biosignal Processing (browser)** | JavaScript — adaptive PPG peak detector, RSA computation |
| **Visualization** | TouchDesigner — generative avatar, GLSL shaders, particle systems |
| **Display** | Two-way mirror with projector/monitor behind glass |

---

## 14. User Journey (End-to-End)

```
Morning
  User puts on EmotiBit wearable
  ↓
All day
  Device records HR, EDA, PPG, motion, temperature to SD card
  ↓
Evening — arrives home
  Plugs EmotiBit into USB → puts it in FTP mode (serial command 'F')
  ↓
  EmoMirror auto-discovers device on local WiFi network (subnet scan)
  Downloads raw recording via FTP
  Runs EmotiBit DataParser → per-sensor .csv files
  ↓
  features.py extracts session-level physiological means
  ml_engine.py classifies dominant state vs. personal baseline
  scoring.py computes Cardiovascular Load + Stress per 5-min epoch (288 epochs)
  review_engine.py finds highlights, selects 3 adaptive questions, builds review JSON
  calculate_baseline.py updates personal baseline for next session
  ↓
Mirror glows to life
  osc_bridge.py sends /emo/mode = "awakening" to TouchDesigner
  Avatar materializes, shaped by today's dominant state and intensity
  ↓
Daily Review scene
  User sees Cardiovascular Load + Stress curves for the day
  Highlights marked on the timeline (anomalous periods ≥ 15 min)
  3 adaptive questions appear, tied to the day's specific peaks
  User reflects and answers in text or by voice
  ↓
Day Recap scene
  Cinematic scroll through 24 significant moments
  Body visualization shifts state for each moment
  User can reply to any moment's reflective question
  ↓
User presses "Restore Balance"
  Biofeedback challenge begins
  Box breathing (4-4-6-2) guides the user
  Live HR and EDA stream in via EmotiBit Oscilloscope → OSC → browser
  RSA meter fills as breathing deepens
  ↓
User breathes slowly, sits still, relaxes
  Avatar transitions: Storm → Focus → Blooming
  ↓
Win: RSA ≥ target for 30 continuous seconds
  "You've returned to your baseline. Carry this calm with you."
  Avatar settles into full bloom
  Mirror fades back to ambient idle
```

---

## 15. What Makes EmoMirror Different

| Aspect | Typical biofeedback apps | EmoMirror |
|--------|--------------------------|-----------|
| **Data richness** | Single sensor (HR only) | 6+ signal streams (HR, EDA, PPG, motion, temp, SCR) |
| **Context** | Real-time only | Full-day retrospective + real-time |
| **Interaction** | Button-based | Purely physiological (breathe to win) |
| **Reflection** | None | Adaptive questions tied to personal peaks |
| **Personalization** | Generic baselines | Personal baseline learned from real history |
| **Memory** | None | Activity memory via cosine similarity |
| **Form factor** | Screen / phone app | Immersive two-way mirror installation |
| **Artistic intent** | Clinical dashboard | Emotional narrative + generative avatar |

---

## 16. Key Numbers

| Metric | Value |
|--------|-------|
| Sensors monitored | 6 signal types, 14+ TypeTags |
| Epoch resolution | 5 minutes (288 epochs per 24-hour day) |
| History depth | 7 days of physiological epochs |
| State categories | 6 (calm, anxious, stressed, active, fatigued, overstimulated) |
| Biofeedback duration | 3 minutes max |
| Win condition | RSA ≥ target for 30 continuous seconds |
| Breathing pattern | 4s inhale / 4s hold / 6s exhale / 2s hold |
| Question bank | 25+ adaptive templates across 5 categories |
| OSC output channels | 18 real-time addresses |
| Activity memory keywords | 17 (run, jog, yoga, meeting, presentation, etc.) |
| Frontend | Single HTML file, no build step required |

---

## 17. What Is Mock or Demo-Only

For the hackathon prototype, a small number of components use hardcoded or pre-baked data:

| Component | Status | Detail |
|-----------|--------|--------|
| `insights.py` | Template stubs | 6 hardcoded state → sentence mappings; no dynamic NLP |
| `question_bank.py` | Partial stubs | Open-reflection fallback questions all use the same template |
| `activity_memory.py` LLM path | Empty stub | `_llm_extract()` function exists but returns nothing; only keyword regex is live |
| `review.json` / `review_data.js` | Pre-baked demo | Generated once by `build_today_review.py`; not regenerated live during demo |
| Day Recap `REPORTS` array | Hardcoded in HTML | 24 entries with hand-written times, descriptions, questions |
| Mic input (day recap) | Mocked | Simulates voice input character-by-character; no real speech recognition |
| Playback scrubber | Visual only | Button animates but does not scrub through real epoch data |
| `emotibit_auto/config.json` | Hardcoded paths | Windows-specific paths and demo FTP credentials |
| TouchDesigner `.toe` file | Not yet built | Architecture fully defined in `touchdesigner/README.md`; no `.toe` in repo |

Everything else — the acquisition pipeline, ML engine, scoring, review engine, biofeedback logic, OSC bridge, WebSocket bridge, PPG peak detector, and the full frontend — is real, functional code.

---

## 18. Limitations & Future Work

| Item | Current status | Future direction |
|------|---------------|-----------------|
| Insight generation | Rule-based templates | LLM-generated personalised insights |
| Activity extraction | Regex keyword list | LLM transcript understanding |
| Question bank | 25 fixed templates | Dynamically generated from history |
| State classification | Rule-based heuristics | Trained model (LSTM / SVM) |
| TouchDesigner avatar | Architecture only | Full `.toe` with GLSL shaders + particles |
| Multi-user support | Single user | Session profiles, shared installation mode |
| FTP trigger | Manual USB + serial `F` | Auto-detect on charge (firmware update) |
| Data storage | Local only | Cloud sync with user-owned storage |

---

*EmoMirror — FrontierInterface Hackathon 2026, Aalto University*
*Track: Storytelling with Biosensing in TouchDesigner*
