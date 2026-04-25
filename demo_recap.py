import sys
from emomirror.ml_engine import StateInferenceEngine
from emomirror.insights import generate_insight

# DEPRECATED: Please use build_today_review.py for Daily Review v2

def demo_recap(filepath):
    print("========================================")
    print("EMO-MIRROR: DAY RECAP DEMO")
    print("========================================")
    print(f"Reading raw data from: {filepath}...\n")
    
    hr_values = []
    ea_values = []
    
    # 1. Parse Data
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    tag = parts[3]
                    if tag == 'HR':
                        for val in parts[6:]:
                            try: hr_values.append(float(val))
                            except ValueError: pass
                    elif tag == 'EA':
                        for val in parts[6:]:
                            try: ea_values.append(float(val))
                            except ValueError: pass
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Filter out garbage noise (Motion Artifacts > 150 BPM)
    hr_values = [h for h in hr_values if 40 <= h <= 150]
    
    total_hr_samples = len(hr_values)
    total_ea_samples = len(ea_values)
    
    if total_hr_samples == 0 or total_ea_samples == 0:
        print("Not enough data for recap.")
        return
        
    print(f"Data loaded successfully. Removing noise...")
    print(f"   Clean HR samples: {total_hr_samples}")
    print(f"   Clean EA samples: {total_ea_samples}\n")
    
    # 2. Split into 3 "Epochs" (e.g., 5 min chunks for the 15 min recording)
    hr_chunk_size = total_hr_samples // 3
    ea_chunk_size = total_ea_samples // 3
    
    engine = StateInferenceEngine()
    
    time_labels = ["Phase 1 (Start)", "Phase 2 (Middle)", "Phase 3 (End)"]
    
    for i in range(3):
        # Slice the chunks
        hr_chunk = hr_values[i*hr_chunk_size : (i+1)*hr_chunk_size]
        ea_chunk = ea_values[i*ea_chunk_size : (i+1)*ea_chunk_size]
        
        # Calculate features
        hr_mean = sum(hr_chunk) / len(hr_chunk)
        ea_mean = sum(ea_chunk) / len(ea_chunk)
        
        features = {
            "hr_mean": hr_mean,
            "eda_mean": ea_mean,
            "activity_mean": 0.5, # Mocking accelerometer
            "temp_mean": 33.0
        }
        
        # Infer State
        result = engine.infer_state(features)
        state_name = result[0] if isinstance(result, tuple) else result
        
        # Generate UI Insight
        insight_text = generate_insight(state_name, features)
        
        # Print Timeline
        print(f"TIME: {time_labels[i]}:")
        print(f"   - Heart Rate : {hr_mean:.1f} BPM")
        print(f"   - EDA / Sweat: {ea_mean:.2f} uS")
        print(f"   - AI State   : [{state_name.upper()}]")
        print(f"   - Mirror UI  : \"{insight_text}\"")
        print("-" * 40)

if __name__ == "__main__":
    demo_recap(r"d:\Frontier Interface\2026-04-24_21-29-04-581986.csv")
