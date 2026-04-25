import os
import json
from emomirror.review_engine import build_day_review
from emomirror.activity_memory import match_signature

def build_today():
    # Synthesize today's data to ensure the demo lands
    # One obvious cardio highlight and one stress highlight
    from seed_history import generate_day_history
    today_epochs = generate_day_history("2026-04-25", "average_day")
    
    # Inject a cardio peak this morning to match "run"
    for i in range(12 * 7, 12 * 8): # 7-8am
        today_epochs[i]['hr_mean'] = 130
        today_epochs[i]['hr_std'] = 25
        today_epochs[i]['activity_mean'] = 1.2
        
    # Inject a stress peak this afternoon (2:15 PM = 14.25 = epoch 171)
    for i in range(171, 178):
        today_epochs[i]['hr_mean'] = 95
        today_epochs[i]['eda_mean'] += 5
        today_epochs[i]['scr_freq'] += 8
        today_epochs[i]['activity_mean'] = 0.1 # low motion
        
    data_dir = os.path.join("data", "demo_user")
    
    # Load user baseline
    with open(os.path.join(data_dir, "user_baseline.json"), "r") as f:
        user_baseline = json.load(f)
        
    # Load activities for matching
    activity_log = []
    log_path = os.path.join(data_dir, "activity_log.jsonl")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    activity_log.append(json.loads(line))
                    
    # We mock finding the cardio highlight features for matching
    hl_features = {"hr_mean": 130, "hr_std": 25, "scr_freq": 2, "activity_mean": 1.2, "duration_min": 60}
    matches = match_signature(hl_features, activity_log)
    
    recent_activities = []
    if matches:
        recent_activities.append({
            "guess": {"activity": matches[0]['activity'], "confidence": matches[0]['similarity']}
        })
    
    review_json = build_day_review("2026-04-25", "demo_user", today_epochs, user_baseline, recent_activities)
    
    with open("review.json", "w") as f:
        json.dump(review_json, f, indent=2)
        
    with open("review_data.js", "w") as f:
        f.write("const reviewDataObj = " + json.dumps(review_json, indent=2) + ";\n")
        
    print("review.json and review_data.js built successfully.")

if __name__ == "__main__":
    build_today()
