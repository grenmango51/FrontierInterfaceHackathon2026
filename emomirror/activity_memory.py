import re
import json
import numpy as np
import os

ACTIVITY_KEYWORDS = ['run', 'ran', 'jog', 'walk', 'football', 'soccer', 'gym', 'lift', 'yoga', 'meeting', 'presentation', 'call', 'meditate', 'sleep', 'nap', 'eat', 'lunch', 'dinner', 'workout']

def _normalize_vector(window_features):
    # simple mock normalization to vector space for cosine distance
    # [hr_mean, hr_std, scr_freq, activity_mean, duration_min]
    v = [
        window_features.get('hr_mean', 70) / 150.0,
        window_features.get('hr_std', 10) / 30.0,
        window_features.get('scr_freq', 2) / 10.0,
        window_features.get('activity_mean', 0.2) / 1.0,
        window_features.get('duration_min', 15) / 120.0
    ]
    return np.array(v)

def log_answer(date, transcript, day_context):
    """
    Regex/keyword extractor is the primary path.
    """
    if os.getenv("EMOMIRROR_USE_LLM") == "1":
        return _llm_extract(transcript)
        
    activity = "unknown"
    lower_t = transcript.lower()
    for kw in ACTIVITY_KEYWORDS:
        if kw in lower_t:
            activity = kw
            break
            
    # Default to linked highlight's window
    hl_features = day_context.get('highlight_features', {})
    
    event = {
        "date": date,
        "activity": activity,
        "transcript": transcript,
        "signature": _normalize_vector(hl_features).tolist()
    }
    
    # Append to jsonl
    log_path = os.path.join("data", "demo_user", "activity_log.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a') as f:
        f.write(json.dumps(event) + '\n')
        
    return event

def match_signature(new_window_features, activity_log, top_k=1):
    """
    Cosine distance on normalized vector.
    """
    if not activity_log:
        return []
        
    v1 = _normalize_vector(new_window_features)
    norm1 = np.linalg.norm(v1)
    if norm1 == 0: norm1 = 1e-5
    
    matches = []
    for entry in activity_log:
        v2 = np.array(entry['signature'])
        norm2 = np.linalg.norm(v2)
        if norm2 == 0: norm2 = 1e-5
        
        sim = np.dot(v1, v2) / (norm1 * norm2)
        if sim >= 0.85:
            matches.append({
                "activity": entry['activity'],
                "similarity": float(sim),
                "date": entry['date']
            })
            
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches[:top_k]

def _llm_extract(transcript):
    # Stub for post-hackathon
    pass
