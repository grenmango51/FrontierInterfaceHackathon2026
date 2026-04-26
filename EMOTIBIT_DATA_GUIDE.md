# Working with Real EmotiBit Data

This guide explains how to connect your EmotiBit wearable to EmoMirror and use real physiological data for both real-time interaction and the Daily Review dashboard.

## 📋 Prerequisites

1.  **EmotiBit Hardware**: An EmotiBit (v4+ recommended) stacked on an Adafruit Feather (ESP32 or M0).
2.  **Network**: Your computer and EmotiBit must be on the same 2.4GHz WiFi network.
3.  **Python 3.9+**: Installed on your computer.
4.  **EmotiBit Software**: Download the [ofxEmotiBit bundle](https://github.com/EmotiBit/ofxEmotiBit/releases/latest) for your OS (Windows/macOS/Linux).

---

## 🛠️ Initial Setup

### 1. Configure WiFi
Follow the [WiFi Configuration section](EmotiBit_Guide.md#wifi-configuration) in the general guide to add your network credentials to the `config.txt` file on your EmotiBit's SD card.

### 2. Install Project Dependencies
In your terminal, navigate to the project root and run:

```bash
# Install core backend dependencies
pip install -r emomirror/requirements.txt

# (Optional) Install automation dependencies
pip install -r emotibit_auto/requirements.txt
```

---

## ⚡ Option 1: Real-Time Streaming (Live Demo)

This mode allows you to see your bio-signals reflected in the UI and TouchDesigner in real time.

### Step A: Start the EmotiBit Oscilloscope
1.  Open the **EmotiBit Oscilloscope** on your computer.
2.  Select your device from the list once it appears.
3.  Ensure data is streaming (you should see the PPG and EDA waves).

### Step B: Enable OSC Output
1.  In the Oscilloscope, go to the **Output List** dropdown.
2.  Select **OSC**.
3.  (First time only) Ensure `oscOutputSettings.xml` is configured to send the required TypeTags (`PG`, `EA`, `HR`, `AX`, etc.) to `127.0.0.1` on port `12345` (default).

### Step C: Run the EmoMirror Bridge
Run the hook script to process the OSC stream and relay it to the UI/TouchDesigner:

```bash
python -m emomirror.hook
```

---

## 📊 Option 2: Automated Data Transfer & Analysis (Daily Review)

This mode is used to download recorded data from your EmotiBit and generate a Daily Review.

### Step A: Record Data
1.  Put your EmotiBit on and start recording by pressing the **Record** button in the Oscilloscope (or via the physical button if configured).
2.  Go about your day or perform a specific activity.
3.  Stop recording when finished.

### Step B: Enter FTP Mode
To transfer data wirelessly:
1.  Connect your EmotiBit to your computer via USB.
2.  Open a Serial Monitor (e.g., Arduino IDE) set to **2,000,000 baud**.
3.  Send the character `F`. The EmotiBit will enter FTP mode.

### Step C: Run the Watcher
Navigate to `emotibit_auto` and run the watcher:

```bash
cd emotibit_auto
python watcher.py
```

The watcher will:
1.  Find the EmotiBit on your network.
2.  Download the latest `.csv` recordings.
3.  Automatically run the **EmotiBit DataParser** to create individual signal files.
4.  Trigger the `emomirror/hook.py` to process the new data.

---

## 🖥️ Viewing the Data in the UI

You can view your real data in the `ui_mockup.html` dashboard using two different methods:

### Method A: Browser-Side Raw CSV Parsing (Fastest)
This method uses a high-performance JavaScript parser inside the browser to process a raw EmotiBit recording.

1.  Place your **Raw EmotiBit CSV** (e.g., `2024-09-18_22-59-45-827135.csv`) in the project root.
2.  Open `ui_mockup.html` in Chrome.
3.  **Toggle CSV Mode**: Press the `M` key to switch the UI into **CSV Mode**.
4.  **Configure Default File**: By default, the UI looks for a specific filename. To change it, update line 27 in `ui_mockup.html`:
    ```javascript
    window.REVIEW_CSV_DEFAULT = './your_actual_filename.csv';
    ```

### Method B: Python-Generated Review JSON
This method uses the Python backend to process your data and generate a `review.json` file, which the UI then loads.

1.  Ensure your parsed data is in `emotibit_data/`.
2.  Run the review builder (this script can be customized to point to your data):
    ```bash
    python build_today_review.py
    ```
3.  The script generates `review.json` and `review_data.js`.
4.  Open `ui_mockup.html` and ensure it is in **Mock/JSON Mode** (Press `M` until the chip says "review.json").

---

## ❓ Troubleshooting

-   **Browser File Access**: If the CSV doesn't load, ensure you are not opening the HTML via `file://` if your browser has strict CORS (though Chrome usually allows it for local files in the same dir). Running a simple server (`npx serve .`) is recommended.
-   **EmotiBit not found**: Ensure you are on a 2.4GHz network. 5GHz is not supported by the Feather board.
-   **Missing TypeTags**: The browser parser requires `HR`, `SF`, and `AX/AY/AZ` tags to be present in the CSV. Ensure these were enabled during recording.
-   **OSC Errors**: Verify that port `12345` is not blocked by a firewall.
