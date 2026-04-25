import os
import json
import random
from emomirror.config import POPULATION_BASELINE

def generate_day_history(date_str, archetype):
    """
    Archetypes: 'hard_workout_morning', 'stressful_meetings', 'restful_weekend', 'average_day'
    Returns 288 epochs.
    """
    epochs = []
    for i in range(288):
        h = (i * 5) // 60
        
        base_hr = POPULATION_BASELINE['hr_mean']
        base_hr_std = POPULATION_BASELINE['hr_std']
        base_eda = POPULATION_BASELINE['eda_mean']
        base_scr = 2.0
        base_act = POPULATION_BASELINE['activity_mean']
        
        # Circadian
        if h < 7 or h > 22:
            base_hr -= 10
            base_eda *= 0.5
            base_act *= 0.1
        
        # Archetypes
        if archetype == 'hard_workout_morning' and 7 <= h <= 8:
            base_hr += 50
            base_hr_std += 15
            base_eda += 3
            base_act += 0.8
        elif archetype == 'stressful_meetings' and 13 <= h <= 15:
            base_hr += 20
            base_eda += 4
            base_scr += 5
            base_act += 0.1 # Low motion
        
        epochs.append({
            "hr_mean": base_hr + random.uniform(-5, 5),
            "hr_std": base_hr_std + random.uniform(-2, 2),
            "eda_mean": base_eda + random.uniform(-0.5, 0.5),
            "scr_freq": base_scr + random.uniform(-1, 1),
            "activity_mean": base_act + random.uniform(-0.05, 0.05),
            "temp_mean": POPULATION_BASELINE['temp_mean'] + random.uniform(-0.2, 0.2)
        })
    return epochs

def seed():
    data_dir = os.path.join("data", "demo_user")
    history_dir = os.path.join(data_dir, "history")
    os.makedirs(history_dir, exist_ok=True)
    
    dates = [f"2026-04-{18+i:02d}" for i in range(7)]
    archetypes = ['restful_weekend', 'average_day', 'hard_workout_morning', 'average_day', 'stressful_meetings', 'average_day', 'average_day']
    
    all_epochs = []
    cardio_peak = 0
    stress_peak = 0
    c_peak_date = ""
    s_peak_date = ""
    
    # We need review_engine methods just to compute averages to build the baseline
    from emomirror.scoring import compute_cardio_score, compute_stress_score
    
    for date, arch in zip(dates, archetypes):
        epochs = generate_day_history(date, arch)
        all_epochs.extend(epochs)
        
        c_scores = [compute_cardio_score(e, POPULATION_BASELINE) for e in epochs]
        s_scores = [compute_stress_score(e, POPULATION_BASELINE) for e in epochs]
        
        c_avg = sum(c_scores)/len(c_scores)
        s_avg = sum(s_scores)/len(s_scores)
        
        if c_avg > cardio_peak:
            cardio_peak = c_avg
            c_peak_date = date
        if s_avg > stress_peak:
            stress_peak = s_avg
            s_peak_date = date
            
        with open(os.path.join(history_dir, f"{date}.json"), "w") as f:
            json.dump({"date": date, "epochs": epochs}, f)
            
    # Compute user baseline
    user_baseline = {
        "hr_mean": sum(e["hr_mean"] for e in all_epochs)/len(all_epochs),
        "hr_std": sum(e["hr_std"] for e in all_epochs)/len(all_epochs),
        "eda_mean": sum(e["eda_mean"] for e in all_epochs)/len(all_epochs),
        "scr_freq_mean": sum(e["scr_freq"] for e in all_epochs)/len(all_epochs),
        "activity_mean": sum(e["activity_mean"] for e in all_epochs)/len(all_epochs),
        "temp_mean": sum(e["temp_mean"] for e in all_epochs)/len(all_epochs),
        "cardio_mean": 45, # mock
        "cardio_std": 10,
        "stress_mean": 40,
        "stress_std": 12,
        "peak_day": {
            "cardio": {"value": cardio_peak, "date": c_peak_date},
            "stress": {"value": stress_peak, "date": s_peak_date}
        }
    }
    with open(os.path.join(data_dir, "user_baseline.json"), "w") as f:
        json.dump(user_baseline, f)
        
    # Pre-populate activity log
    from emomirror.activity_memory import _normalize_vector
    activities = [
        {"date": dates[2], "activity": "run", "transcript": "Morning run", "signature": _normalize_vector({"hr_mean": 120, "hr_std": 20, "scr_freq": 3, "activity_mean": 1.0, "duration_min": 60}).tolist()},
        {"date": dates[4], "activity": "presentation", "transcript": "Big presentation", "signature": _normalize_vector({"hr_mean": 90, "hr_std": 12, "scr_freq": 7, "activity_mean": 0.1, "duration_min": 120}).tolist()}
    ]
    with open(os.path.join(data_dir, "activity_log.jsonl"), "w") as f:
        for act in activities:
            f.write(json.dumps(act) + "\n")

if __name__ == "__main__":
    seed()
