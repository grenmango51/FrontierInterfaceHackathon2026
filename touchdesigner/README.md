# EmoMirror: TouchDesigner Integration

This document outlines how to connect the TouchDesigner visual engine to the EmoMirror Python backend.

## Architecture
The EmoMirror Python backend processes data from the EmotiBit SD card and sends it to TouchDesigner via OSC over UDP.

*   **Port:** 7400
*   **IP Address:** 127.0.0.1 (localhost)

## OSC Messages Reference

TouchDesigner should listen for the following OSC addresses:

| Address | Type | Description |
| :--- | :--- | :--- |
| `/emo/mode` | string | Current operating mode (`awakening`, `live`, etc.) |
| `/emo/state/current` | string | Inferred state (`calm`, `stressed`, `anxious`, `active`, `fatigued`, `overstimulated`) |
| `/emo/state/intensity` | float | State intensity (0.0 - 1.0) |
| `/emo/state/glitch` | float | Recommended distortion factor (0.0 - 1.0) |
| `/emo/state/color/r` | float | Suggested state color R (0.0 - 1.0) |
| `/emo/state/color/g` | float | Suggested state color G (0.0 - 1.0) |
| `/emo/state/color/b` | float | Suggested state color B (0.0 - 1.0) |
| `/emo/hr/current` | float | Average Heart Rate (BPM) |
| `/emo/hr/deviation` | float | HR deviation from baseline (std devs) |
| `/emo/eda/current` | float | Average EDA |
| `/emo/eda/deviation` | float | EDA deviation from baseline (std devs) |
| `/emo/motion/level` | float | Inferred activity variance |
| `/emo/temp/current` | float | Average Skin Temperature (°C) |
| `/emo/insight` | string | Natural language insight based on the data |

## TouchDesigner Setup

1.  Add an **OSC In CHOP**.
2.  Set the **Network Port** to `7400`.
3.  Add a **Select CHOP** after the OSC In CHOP to isolate specific channels (e.g., `*state/color*`, `*state/intensity*`).
4.  Use **Math CHOPs** to map these normalized values (0-1) to your visual parameters (e.g., noise scale, particle emission rate, or shader uniforms).
5.  Use an **OSC In DAT** on the same port to capture string messages like `/emo/state/current` and `/emo/insight`. Convert these to text using a **Text TOP** for the UI overlay.

### Unified Biofeedback Scene (Particle Cleansing)

When the user enters Biofeedback mode (`/emo/biofeedback/active` = 1), the visual engine should transition the Avatar into the interactive game state.

Map the `/emo/biofeedback/progress` channel (0.0 to 1.0) to drive the particle system:
*   **0.0 (The Storm):** High Noise/Turbulence, fast particle speed, chaotic birth rate.
*   **0.5 (The Focus):** Decreasing noise, stabilizing particle flow.
*   **1.0 (The Blooming):** Zero noise, smooth orbital velocity, symmetrical form, color shift to calming Teal/Blue.

Overlay the string from `/emo/biofeedback/instruction` to guide the user's breathing and posture.

*For real-time biofeedback*, you will also need to run the EmotiBit Oscilloscope and route its OSC output (typically port `12345`) to the backend.
