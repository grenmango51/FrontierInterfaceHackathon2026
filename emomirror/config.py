# emomirror/config.py
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# OSC Configuration
OSC_IP = "127.0.0.1"
OSC_PORT_OUT = 7400  # Port to send data to TouchDesigner

# Feature Extraction Settings
EPOCH_DURATION_SEC = 300  # 5 minutes per segment
POPULATION_BASELINE = {
    "hr_mean": 70.0,
    "hr_std": 10.0,
    "eda_mean": 2.0,
    "eda_std": 0.5,
    "activity_mean": 0.2,
    "temp_mean": 33.0
}
