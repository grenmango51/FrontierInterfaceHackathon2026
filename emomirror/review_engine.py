import math
from .scoring import compute_cardio_score, compute_stress_score
from .question_bank import bank
from .ml_engine import StateInferenceEngine
from .insights import generate_insight

def smooth_curve(scores, window=6):
    """30-min moving avg (window=6 for 5-min epochs). Smoothing: 0.8 * old + 0.2 * new style"""
    smoothed = []
    if not scores: return []
    # simple moving average for demo
    for i in range(len(scores)):
        start = max(0, i - window + 1)
        chunk = scores[start:i+1]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed

def detect_highlights(epoch_scores, personal_mean, personal_std, metric_name):
    """
    Find contiguous epochs where score > mean + 1.5σ and duration >= 15 min (3 epochs).
    Merges adjacent runs <= 5min apart.
    """
    threshold = personal_mean + 1.5 * personal_std
    highlights = []
    
    current_run = []
    for i, score in enumerate(epoch_scores):
        if score > threshold:
            current_run.append(i)
        else:
            if current_run:
                # evaluate run
                if len(current_run) >= 3:
                    highlights.append(current_run)
                current_run = []
    if current_run and len(current_run) >= 3:
        highlights.append(current_run)
        
    # Format
    res = []
    for idx, run in enumerate(highlights[:2]): # Top 2
        start_idx = run[0]
        end_idx = run[-1]
        
        # 5 min per epoch
        start_min = start_idx * 5
        end_min = (end_idx + 1) * 5
        
        peak = max([epoch_scores[i] for i in run])
        pct_above = ((peak - personal_mean) / personal_mean) * 100 if personal_mean > 0 else 0
        
        # Format time e.g., 00:00 -> HH:MM
        sh = start_min // 60
        sm = start_min % 60
        eh = end_min // 60
        em = end_min % 60
        
        res.append({
            "metric": metric_name,
            "id": f"{metric_name}.{idx}",
            "start": f"{sh:02d}:{sm:02d}",
            "end": f"{eh:02d}:{em:02d}",
            "peak": int(peak),
            "pct_above_mean": int(pct_above),
            "duration_min": (end_idx - start_idx + 1) * 5,
            "start_idx": start_idx,
            "end_idx": end_idx
        })
        
    return res

def summarize_day(epoch_scores_cardio, epoch_scores_stress, user_baseline, features_avg):
    cardio_avg = sum(epoch_scores_cardio) / len(epoch_scores_cardio) if epoch_scores_cardio else 0
    stress_avg = sum(epoch_scores_stress) / len(epoch_scores_stress) if epoch_scores_stress else 0
    
    # ML Engine
    engine = StateInferenceEngine()
    state_result = engine.infer_state(features_avg)
    dominant_state = state_result[0]
    tagline = generate_insight(dominant_state, features_avg)

    peak_day = user_baseline.get('peak_day', {})
    
    # Calculate VS baseline percent
    cardio_baseline = user_baseline.get('cardio_mean', 50)
    stress_baseline = user_baseline.get('stress_mean', 50)
    
    c_vs = ((cardio_avg - cardio_baseline) / cardio_baseline * 100) if cardio_baseline else 0
    s_vs = ((stress_avg - stress_baseline) / stress_baseline * 100) if stress_baseline else 0
    
    return {
        "cardio_avg": int(cardio_avg),
        "cardio_vs_baseline_pct": int(c_vs),
        "cardio_peak_historical": int(peak_day.get('cardio', {}).get('value', 100)),
        "cardio_peak_date": peak_day.get('cardio', {}).get('date', '1970-01-01'),
        
        "stress_avg": int(stress_avg),
        "stress_vs_baseline_pct": int(s_vs),
        "stress_peak_historical": int(peak_day.get('stress', {}).get('value', 100)),
        "stress_peak_date": peak_day.get('stress', {}).get('date', '1970-01-01'),
        
        "dominant_state": dominant_state,
        "tagline": tagline
    }

def pick_questions(day_summary, highlights, recent_activities, question_bank, history):
    # Simplified question picker
    scores = []
    
    for q in question_bank:
        # Match triggers
        triggers = q['triggers']
        match_strength = 1.0
        
        metric_trigger = triggers.get("metric")
        if metric_trigger:
            matching_hl = [h for h in highlights if h['metric'] == metric_trigger]
            if not matching_hl:
                match_strength = 0.0
                
        state_trigger = triggers.get("dominant_state")
        if state_trigger and state_trigger != day_summary['dominant_state']:
            match_strength = 0.0
            
        has_guess = triggers.get("has_guess")
        if has_guess and not any(r.get('guess') for r in recent_activities):
            match_strength = 0.0
            
        if match_strength == 0.0:
            continue
            
        novel = 1.0
        cool = 1.0 # mock cooldown
        fit = match_strength * (0.6 + 0.4 * q['specificity']) * novel * cool * q['priority_base']
        scores.append((fit, q))
        
    scores.sort(key=lambda x: x[0], reverse=True)
    
    # Enforce diversity
    selected = []
    seen_categories = set()
    for fit, q in scores:
        if q['category'] not in seen_categories:
            seen_categories.add(q['category'])
            # Bind text template
            text = q['text_template']
            linked_hl = None
            guess = None
            if q['category'] == 'anomaly_probe' and q['triggers'].get('metric'):
                hl = next((h for h in highlights if h['metric'] == q['triggers']['metric']), None)
                if hl:
                    text = text.format(start=hl['start'], end=hl['end'], pct=hl['pct_above_mean'], duration=hl['duration_min'])
                    linked_hl = hl['id']
            elif q['category'] == 'pattern_reinforce':
                hl = next((h for h in highlights if h['metric'] == 'cardio'), highlights[0] if highlights else None)
                guess_obj = next((r for r in recent_activities if r.get('guess')), None)
                if hl and guess_obj:
                    text = text.format(start=hl['start'], end=hl['end'], activity=guess_obj['guess']['activity'])
                    linked_hl = hl['id']
                    guess = guess_obj['guess']
                else:
                    continue # skip if can't bind
                    
            selected.append({
                "id": q['id'],
                "category": q['category'],
                "text": text,
                "linked_highlight": linked_hl,
                "guess": guess
            })
            if len(selected) >= 3:
                break
                
    return selected

def build_day_review(date, user_id, epoch_features_list, user_baseline, recent_activities=[]):
    """
    Main orchestrator
    """
    cardio_scores = []
    stress_scores = []
    
    for feats in epoch_features_list:
        cardio_scores.append(compute_cardio_score(feats, user_baseline))
        stress_scores.append(compute_stress_score(feats, user_baseline))
        
    smooth_cardio = smooth_curve(cardio_scores)
    smooth_stress = smooth_curve(stress_scores)
    
    c_mean = user_baseline.get('cardio_mean', 50)
    c_std = user_baseline.get('cardio_std', 15)
    s_mean = user_baseline.get('stress_mean', 50)
    s_std = user_baseline.get('stress_std', 15)
    
    c_highlights = detect_highlights(cardio_scores, c_mean, c_std, "cardio")
    s_highlights = detect_highlights(stress_scores, s_mean, s_std, "stress")
    highlights = c_highlights + s_highlights
    
    # average features for the day
    features_avg = {}
    if epoch_features_list:
        for k in epoch_features_list[0].keys():
            features_avg[k] = sum(f[k] for f in epoch_features_list if k in f) / len(epoch_features_list)
            
    summary = summarize_day(cardio_scores, stress_scores, user_baseline, features_avg)
    
    # map scores to time series (HH:MM)
    c_curve = []
    s_curve = []
    for i in range(len(smooth_cardio)):
        mins = i * 5
        h = mins // 60
        m = mins % 60
        t_str = f"{h:02d}:{m:02d}"
        c_curve.append({"t": t_str, "v": int(smooth_cardio[i])})
        s_curve.append({"t": t_str, "v": int(smooth_stress[i])})
        
    dashboards = {
        "cardio": {
            "label": "Cardiovascular Load",
            "unit": "score",
            "curve": c_curve,
            "baseline_line": int(c_mean),
            "gauge": {
                "value": summary['cardio_avg'],
                "peak": summary['cardio_peak_historical'],
                "fill_pct": min(1.0, summary['cardio_avg'] / 100.0),
                "delta_pct": summary['cardio_vs_baseline_pct']
            },
            "highlights": c_highlights
        },
        "stress": {
            "label": "Stress & Arousal",
            "unit": "score",
            "curve": s_curve,
            "baseline_line": int(s_mean),
            "gauge": {
                "value": summary['stress_avg'],
                "peak": summary['stress_peak_historical'],
                "fill_pct": min(1.0, summary['stress_avg'] / 100.0),
                "delta_pct": summary['stress_vs_baseline_pct']
            },
            "highlights": s_highlights
        }
    }
    
    questions = pick_questions(summary, highlights, recent_activities, bank, [])
    
    # Fill remaining questions if < 3
    if len(questions) < 3:
        for q in bank:
            if q['category'] == 'open_reflection' and not any(sq['id'] == q['id'] for sq in questions):
                questions.append({
                    "id": q['id'],
                    "category": q['category'],
                    "text": q['text_template'],
                    "linked_highlight": None,
                    "guess": None
                })
            if len(questions) >= 3:
                break
    
    return {
        "date": date,
        "user_id": user_id,
        "summary": summary,
        "dashboards": dashboards,
        "questions": questions[:3]
    }
