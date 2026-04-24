import json
import pandas as pd
import numpy as np
from pathlib import Path
from .features import extract_features
from .config import DATA_DIR

def calculate_daily_baseline(parsed_files_list, user_id="default_user"):
    """
    Takes a list of parsed CSV files (e.g., a full day's recording),
    calculates the average features, and saves them as the user's personal baseline.
    """
    print("Calculating true physiological baseline from full day data...")
    
    # We can just pass the whole list of files to extract_features, 
    # since extract_features reads the mean of the entire file.
    # If parsed_files_list contains multiple days, it will average them all.
    features = extract_features(parsed_files_list)
    
    # We also need standard deviations for the Z-score logic in ml_engine
    stds = {
        "hr_std": 10.0, # Default fallback
        "eda_std": 0.5,
    }
    
    # Calculate true STD if possible
    files_by_tag = {p.name.split("_")[-1].replace(".csv", ""): p for p in parsed_files_list if "_" in p.name}
    
    if "HR" in files_by_tag:
        df_hr = pd.read_csv(files_by_tag["HR"])
        stds["hr_std"] = df_hr["HR"].std()
        
    if "EA" in files_by_tag:
        df_ea = pd.read_csv(files_by_tag["EA"])
        stds["eda_std"] = df_ea["EA"].std()
        
    # Construct new baseline
    new_baseline = {
        "hr_mean": features.get("hr_mean", 70.0),
        "hr_std": stds["hr_std"],
        "eda_mean": features.get("eda_mean", 2.0),
        "eda_std": stds["eda_std"],
        "activity_mean": features.get("activity_mean", 0.2),
        "temp_mean": features.get("temp_mean", 33.0)
    }
    
    # Ensure no NaN values
    for k, v in new_baseline.items():
        if pd.isna(v):
            new_baseline[k] = 0.0 # Or fallback to population
            
    # Save to JSON
    user_dir = DATA_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = user_dir / "user_baseline.json"
    
    with open(baseline_file, "w") as f:
        json.dump(new_baseline, f, indent=4)
        
    print(f"Personal baseline saved to {baseline_file}")
    print(json.dumps(new_baseline, indent=2))
    return new_baseline
