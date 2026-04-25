import numpy as np

def compute_cardio_score(epoch_features, personal_baseline):
    """
    Weighted: 0.5 * HR_pct + 0.3 * hr_std_pct + 0.2 * motion_pct.
    HR_pct is HR percentile vs personal baseline.
    Returns 0-100 float.
    """
    # Helper to calculate pseudo-percentile based on mean and std
    def calc_pct(val, mean, std):
        if std == 0: return 50.0
        z = (val - mean) / std
        # rough z-score to percentile mapping (clipped)
        pct = (z + 3) / 6 * 100
        return max(0.0, min(100.0, pct))
        
    hr_pct = calc_pct(epoch_features.get('hr_mean', 70), personal_baseline.get('hr_mean', 70), personal_baseline.get('hr_std', 10))
    hr_std_pct = calc_pct(epoch_features.get('hr_std', 10), personal_baseline.get('hr_std', 10), personal_baseline.get('hr_std_std', 5))
    motion_pct = calc_pct(epoch_features.get('activity_mean', 0.2), personal_baseline.get('activity_mean', 0.2), personal_baseline.get('activity_std', 0.1))

    return 0.5 * hr_pct + 0.3 * hr_std_pct + 0.2 * motion_pct

def compute_stress_score(epoch_features, personal_baseline):
    """
    Weighted: 0.5 * SCR_freq_pct + 0.3 * EDA_tonic_pct + 0.2 * temp_drop_bonus
    Multiplied by low_motion_gate = max(0.3, 1.0 - motion_norm)
    """
    def calc_pct(val, mean, std):
        if std == 0: return 50.0
        z = (val - mean) / std
        pct = (z + 3) / 6 * 100
        return max(0.0, min(100.0, pct))

    scr_freq = epoch_features.get('scr_freq', 0)
    scr_freq_pct = calc_pct(scr_freq, personal_baseline.get('scr_freq_mean', 2), personal_baseline.get('scr_freq_std', 1))
    
    eda_tonic = epoch_features.get('eda_mean', 2.0)
    eda_tonic_pct = calc_pct(eda_tonic, personal_baseline.get('eda_mean', 2.0), personal_baseline.get('eda_std', 0.5))
    
    temp_drop = personal_baseline.get('temp_mean', 33.0) - epoch_features.get('temp_mean', 33.0)
    temp_drop_bonus = max(0, min(100, temp_drop * 50)) # 2 degree drop -> 100 bonus

    raw_stress = 0.5 * scr_freq_pct + 0.3 * eda_tonic_pct + 0.2 * temp_drop_bonus
    
    motion = epoch_features.get('activity_mean', 0.2)
    motion_norm = max(0.0, min(1.0, motion / (personal_baseline.get('activity_mean', 0.2) + 2*personal_baseline.get('activity_std', 0.1))))
    low_motion_gate = max(0.3, 1.0 - motion_norm)
    
    return raw_stress * low_motion_gate

def derive_scr_events(eda_series, fs):
    """
    Simple peak detector.
    Rolling-baseline subtraction -> threshold at 0.05 uS rise -> minimum inter-peak gap 1s.
    Returns [{t, amplitude, rise_time}]
    """
    if len(eda_series) < int(fs * 2):
        return []
        
    # very simple peak detection for demo
    events = []
    threshold = 0.05
    min_gap = fs * 1.0
    
    # approximate moving average
    window = int(fs * 4)
    if window == 0: window = 1
    
    if isinstance(eda_series, list):
        eda_series = np.array(eda_series)
        
    last_peak_idx = -min_gap
    
    for i in range(window, len(eda_series)):
        baseline = np.mean(eda_series[i-window:i])
        val = eda_series[i]
        
        if val - baseline > threshold and (i - last_peak_idx) >= min_gap:
            events.append({
                't': i / fs,
                'amplitude': val - baseline,
                'rise_time': 1.0 # mock
            })
            last_peak_idx = i
            
    return events
