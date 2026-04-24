def generate_insight(state, features):
    """
    Generates a simple natural language insight based on the current features and inferred state.
    """
    hr = features.get("hr_mean")
    eda = features.get("eda_mean")
    
    if state == "overstimulated":
        return f"High stimulation detected. Heart rate is around {hr:.0f} BPM." if hr else "High stimulation detected in your biosignals."
    elif state == "stressed":
        return "You've had a tense period recently. Consider a moment of decompression."
    elif state == "anxious":
        return "I sense some lingering tension. Would you like a breathing exercise?"
    elif state == "active":
        return f"Great activity! Heart rate reached {hr:.0f} BPM." if hr else "Great activity detected!"
    elif state == "fatigued":
        return "You seem drained. Your body might need rest or recovery."
    elif state == "calm":
        return "Your body is in a state of calm balance."
        
    return "Analyzing your daily biosignal patterns..."
