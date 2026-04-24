import pandas as pd
import numpy as np

def extract_features(parsed_files):
    """
    Given a list of parsed CSV file paths from EmotiBit DataParser,
    extracts basic physiological features for the MVP.
    """
    features = {
        "hr_mean": None,
        "eda_mean": None,
        "activity_mean": None,
        "temp_mean": None
    }
    
    # Simple dictionary to group files by typetag
    files_by_tag = {}
    for p in parsed_files:
        filename = p.name
        if "_" in filename:
            tag = filename.split("_")[-1].replace(".csv", "")
            files_by_tag[tag] = p
            
    # Heart Rate
    if "HR" in files_by_tag:
        try:
            df_hr = pd.read_csv(files_by_tag["HR"])
            features["hr_mean"] = df_hr["HR"].mean()
        except Exception as e:
            print(f"Error reading HR: {e}")
            
    # EDA
    if "EA" in files_by_tag:
        try:
            df_ea = pd.read_csv(files_by_tag["EA"])
            features["eda_mean"] = df_ea["EA"].mean()
        except Exception as e:
            print(f"Error reading EA: {e}")
            
    # Temperature (T1 or TH)
    temp_tag = "T1" if "T1" in files_by_tag else "TH"
    if temp_tag in files_by_tag:
        try:
            df_t = pd.read_csv(files_by_tag[temp_tag])
            features["temp_mean"] = df_t[temp_tag].mean()
        except Exception as e:
            print(f"Error reading Temp: {e}")
            
    # Motion (Approximated as variance of AX, AY, AZ)
    try:
        activity_components = []
        for tag in ["AX", "AY", "AZ"]:
            if tag in files_by_tag:
                df_a = pd.read_csv(files_by_tag[tag])
                activity_components.append(df_a[tag].var())
        if activity_components:
            features["activity_mean"] = np.mean(activity_components)
    except Exception as e:
        print(f"Error reading Accelerometer: {e}")
        
    return features
