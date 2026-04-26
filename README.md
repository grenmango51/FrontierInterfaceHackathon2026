# EmoMirror

**FrontierInterface Hackathon 2026 — Aalto University**  
Track: Storytelling with Biosensing in TouchDesigner

EmoMirror is a biosignal-driven interactive art installation. It reads physiological data from an **EmotiBit wearable** (heart rate, EDA/sweat, motion, temperature), infers the wearer's emotional state in real time, and mirrors it back through a cinematic holographic avatar UI.

---

## Demo

Open `ui_mockup.html` directly in Chrome — no build step, no server needed.

Press `D` to run the full 18-second demo sequence.

The UI follows a 3-scene narrative arc:

| Scene | Emotional State | Visual |
|---|---|---|
| 1 — Awakening | STORM (stressed/anxious) | Red glitching wireframe, harsh particles |
| 2 — Cleansing | CALMING | Cyan holographic figure, biofeedback ring |
| 3 — Bloom | RELEASE | Gold dissolving figure, particle burst |

---

## Running the Daily Review

The Daily Review dashboard in `ui_mockup.html` requires a `review.json` payload. To generate it with synthetic data:

```bash
python seed_history.py        # generates 7-day history in data/demo_user/history/
python build_today_review.py  # outputs review.json
```

Then reload `ui_mockup.html`.

---

## Repository Layout

```
FrontierInterface/
├── ui_mockup.html          ← Main demo file (open in Chrome)
├── biosignal.js            ← Browser-side PPG peak detection & adaptive threshold
├── csv_parser.js           ← High-performance streaming CSV parser (typed arrays)
├── build_today_review.py   ← Generates review.json for the Daily Review scene
├── seed_history.py         ← Generates synthetic 7-day history for demo
├── emomirror/              ← Python backend
│   ├── scoring.py          ← Composite stress/cardio scoring (motion-gated)
│   ├── ml_engine.py        ← Rule-based emotional state inference
│   ├── activity_memory.py  ← Cosine similarity activity signature matching
│   ├── features.py         ← Feature extraction from raw biosignal windows
│   ├── review_engine.py    ← Daily Review JSON orchestrator
│   ├── question_bank.py    ← Adaptive question templates
│   ├── osc_bridge.py       ← OSC → TouchDesigner bridge (port 7400)
│   └── biofeedback.py      ← Real-time biofeedback loop
└── emotibit_auto/          ← EmotiBit auto-discovery, transfer, and parsing utilities
```

---

## Python Backend

The backend connects to an EmotiBit wearable over the network and streams biosignal features to TouchDesigner via OSC.

```bash
pip install -r emomirror/requirements.txt
python emomirror/hook.py
```

State inference output: `(state_name, intensity, deviations)` where state is one of `calm`, `anxious`, `stressed`, `active`, `fatigued`, `overstimulated`.

---

## Key Technical Highlights

- **Motion-gated stress scoring** — attenuates EDA stress scores during high-motion periods to avoid false positives from exercise
- **Browser-side signal processing** — `biosignal.js` runs an adaptive-threshold PPG peak detector entirely in the browser, reducing latency
- **Streaming CSV parser** — `csv_parser.js` uses typed arrays to parse 200MB EmotiBit recordings in seconds without blocking the UI thread
- **Cosine similarity memory** — `activity_memory.py` matches current activity signatures against stored history for personalized reflections
