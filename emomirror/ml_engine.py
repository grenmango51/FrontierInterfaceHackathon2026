import json
from pathlib import Path
from .config import POPULATION_BASELINE, DATA_DIR

class StateInferenceEngine:
    def __init__(self, user_id="default_user"):
        # Start with population baseline
        self.baseline = POPULATION_BASELINE.copy()
        
        # Try to load personal baseline if it exists
        user_baseline_file = DATA_DIR / user_id / "user_baseline.json"
        if user_baseline_file.exists():
            try:
                with open(user_baseline_file, "r") as f:
                    personal_baseline = json.load(f)
                    self.baseline.update(personal_baseline)
                print(f"ML Engine: Loaded personal baseline for {user_id}")
            except Exception as e:
                print(f"ML Engine: Failed to load personal baseline, using population defaults. Error: {e}")
        else:
            print("ML Engine: No personal baseline found, using population defaults.")

    def infer_state(self, features):
        """
        Rule-based state inference based on deviations from baseline.
        Returns a tuple: (state_name, dict_of_deviations)
        """
        # Calculate deviations (in standard deviations or raw differences if std is 0)
        deviations = {}
        
        hr = features.get("hr_mean")
        if hr is not None:
            deviations["hr"] = (hr - self.baseline["hr_mean"]) / self.baseline["hr_std"]
        else:
            deviations["hr"] = 0.0
            
        eda = features.get("eda_mean")
        if eda is not None:
            deviations["eda"] = (eda - self.baseline["eda_mean"]) / self.baseline["eda_std"]
        else:
            deviations["eda"] = 0.0
            
        activity = features.get("activity_mean")
        if activity is not None:
            # simple scaling for activity
            deviations["activity"] = activity - self.baseline["activity_mean"]
        else:
            deviations["activity"] = 0.0
            
        # Inference Rules
        state = "calm"  # default
        intensity = 0.0
        
        d_hr = deviations["hr"]
        d_eda = deviations["eda"]
        act = deviations["activity"]
        
        if d_hr > 2.0 and d_eda > 2.0:
            state = "overstimulated"
            intensity = min(max(d_hr, d_eda) / 4.0, 1.0)
        elif d_hr > 1.5 and d_eda > 1.5:
            state = "stressed"
            intensity = min(max(d_hr, d_eda) / 3.0, 1.0)
        elif d_hr > 1.0 and d_eda > 1.0 and act < 0.5:
            state = "anxious"
            intensity = min(d_eda / 2.0, 1.0)
        elif act > 1.0 and d_hr > 1.5:
            state = "active"
            intensity = min(act / 2.0, 1.0)
        elif d_hr < -0.5 and act < -0.1:
            state = "fatigued"
            intensity = min(abs(d_hr), 1.0)
        else:
            state = "calm"
            # How close to perfect baseline
            intensity = max(1.0 - (abs(d_hr) + abs(d_eda)) / 2.0, 0.0)
            
        return state, intensity, deviations
