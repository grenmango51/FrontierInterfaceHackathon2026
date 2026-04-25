# EmoMirror — Project Overview

**Event:** FrontierInterface Hackathon 2026 (Aalto University)
**Track:** Storytelling with Biosensing in TouchDesigner
**Team:** Hoai Anh Nguyen

---

## What it is

EmoMirror is a biosignal-driven interactive art installation. It reads physiological data from an **EmotiBit wearable** (heart rate, EDA/sweat, motion, temperature), infers the wearer's emotional state in real time, and mirrors that state back through a cinematic holographic avatar UI.

The demo UI is a **3-scene narrative arc**:

| Scene | State | Visual |
|---|---|---|
| 1 — Awakening | STORM (stressed/anxious) | Red glitching wireframe figure, harsh particles |
| 2 — Cleansing | CALMING | Cyan holographic figure, smooth biofeedback ring |
| 3 — Bloom | RELEASE | Gold dissolving figure, particle burst |

---

## Repository layout

 FrontierInterface/
 ├── ui_mockup.html          ← THE DEMO FILE. Single self-contained HTML, open in Chrome
 ├── Challenge.md            ← Hackathon brief + biosensor metric definitions
 ├── demo_recap.py           ← CLI script: parse a CSV recording → print 3-phase state recap (DEPRECATED)
 ├── 2026-04-24_21-29-04-581986.csv  ← Sample EmotiBit recording (~15 min)
 ├── build_today_review.py   ← Generates review.json for Daily Review v2
 ├── seed_history.py         ← Generates synthetic 7-day history for Daily Review v2
 ├── emomirror/              ← Python backend modules
 │   ├── config.py           ← OSC config, baseline population stats
 │   ├── ml_engine.py        ← Rule-based state inference (calm/anxious/stressed/active/fatigued)
 │   ├── insights.py         ← Generates human-readable insight strings per state
 │   ├── features.py         ← Feature extraction from raw biosignal windows
 │   ├── biofeedback.py      ← Real-time biofeedback loop
 │   ├── osc_bridge.py       ← OSC → TouchDesigner bridge (port 7400)
 │   ├── hook.py             ← Hooks into EmotiBit data stream
 │   ├── preference.py       ← User preference / personalization
 │   ├── calculate_baseline.py ← Computes personal vs. population baseline
 │   ├── scoring.py          ← Composite score math (Cardio, Stress)
 │   ├── review_engine.py    ← Orchestrator for Daily Review JSON payload
 │   ├── question_bank.py    ← Templates for adaptive questions
 │   └── activity_memory.py  ← Regex/keyword extraction and signature matching
 └── emotibit_auto/          ← Utility scripts: auto-discover, transfer, parse EmotiBit files
```

### Daily Review v2
A new data-rich reflective dashboard and adaptive questions engine is built on top of the original prototype. To test the review scene in `ui_mockup.html`, first run `python seed_history.py` to generate an artificial 7-day history in `data/demo_user/history`, and then run `python build_today_review.py` to output the `review.json` consumed by the frontend.


---

## Key technical facts

**Frontend (ui_mockup.html)**
- No build step — open directly in Chrome
- GSAP 3.12.5 (CDN) drives all animations via `avatarState` object
- Canvas (`z-index: 0`) renders aura glow, ambient particles, biofeedback ring
- SVG avatar figure (`z-index: 2`) is currently a hand-drawn canvas bezier blob — **needs replacement** with an inlined CC0 anatomy SVG (see AGENT_HANDOFF.md)
- Press `D` to run full 18-second demo sequence
- Design tokens in `:root`: `--state-storm` (red), `--state-calming` (cyan `#4AC8FF`), `--state-bloom` (gold `#FFD89E`)

**Backend (Python)**
- `StateInferenceEngine.infer_state(features)` → returns `(state_name, intensity, deviations)`
- States: `calm`, `anxious`, `stressed`, `active`, `fatigued`, `overstimulated`
- Inference is rule-based (deviation from personal/population baseline in σ units)
- OSC bridge sends processed state to TouchDesigner on `127.0.0.1:7400`
- Personal baseline stored at `data/<user_id>/user_baseline.json`

**Data format (EmotiBit CSV)**
- Columns: `timestamp, packet_id, ?, tag, ?, ?, value1, value2, ...`
- Key tags: `HR` (heart rate BPM), `EA` (electrodermal activity µS), `AX/AY/AZ` (accelerometer), `GX/GY/GZ` (gyroscope), `TW` (thermopile temperature)
- Valid HR range after noise filter: 40–150 BPM

---


## Biosensor metrics cheat sheet

| Tag | Metric | Notes |
|---|---|---|
| HR | Heart rate (BPM) | Derived from PPG |
| EA | Electrodermal activity (µS) | EDA baseline — stress/arousal |
| PI | SCR amplitude | Intensity of a sweat spike |
| PF | SCR frequency | Sweat spikes per minute |
| PR | SCR rise time | How fast the spike builds |
| AX/AY/AZ | Accelerometer | Linear movement |
| GX/GY/GZ | Gyroscope | Rotation |
| MX/MY/MZ | Magnetometer | Compass orientation |
| TW | Skin temperature (°C) | ~33°C baseline |
