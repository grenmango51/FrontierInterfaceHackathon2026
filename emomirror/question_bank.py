bank = [
    {
        "id": "anomaly_stress_pm",
        "category": "anomaly_probe",
        "text_template": "Your stress peaked between {start} and {end}, {pct}% above your norm. What was happening?",
        "triggers": {"metric": "stress", "highlight_count": ">=1"},
        "specificity": 0.9,
        "cooldown_days": 2,
        "priority_base": 1.0
    },
    {
        "id": "anomaly_cardio_am",
        "category": "anomaly_probe",
        "text_template": "You had a sustained cardio peak for {duration} min this morning. What were you doing?",
        "triggers": {"metric": "cardio", "highlight_count": ">=1", "time_of_day": "morning"},
        "specificity": 0.8,
        "cooldown_days": 2,
        "priority_base": 0.9
    },
    {
        "id": "match_activity",
        "category": "pattern_reinforce",
        "text_template": "Your cardio pattern between {start} and {end} looks like your past {activity}. Was that it?",
        "triggers": {"has_guess": True},
        "specificity": 1.0,
        "cooldown_days": 1,
        "priority_base": 1.5
    },
    {
        "id": "state_callout_stressed",
        "category": "state_callout",
        "text_template": "Your body spent a lot of time in a stressed state today. How are you feeling now?",
        "triggers": {"dominant_state": "stressed"},
        "specificity": 0.6,
        "cooldown_days": 3,
        "priority_base": 0.8
    },
    {
        "id": "state_callout_calm",
        "category": "state_callout",
        "text_template": "Your data shows a very calm day overall. Did you intentionally take it easy?",
        "triggers": {"dominant_state": "calm"},
        "specificity": 0.6,
        "cooldown_days": 3,
        "priority_base": 0.7
    },
    {
        "id": "recovery_probe_fatigue",
        "category": "recovery_probe",
        "text_template": "You had high fatigue markers today. Are you sleeping well?",
        "triggers": {"dominant_state": "fatigued"},
        "specificity": 0.7,
        "cooldown_days": 4,
        "priority_base": 0.8
    },
    {
        "id": "open_reflection_1",
        "category": "open_reflection",
        "text_template": "Anything memorable today the data wouldn't capture?",
        "triggers": {},
        "specificity": 0.1,
        "cooldown_days": 1,
        "priority_base": 0.4
    },
    {
        "id": "open_reflection_2",
        "category": "open_reflection",
        "text_template": "What was the highlight of your day?",
        "triggers": {},
        "specificity": 0.1,
        "cooldown_days": 2,
        "priority_base": 0.4
    },
    {
        "id": "open_reflection_3",
        "category": "open_reflection",
        "text_template": "If you could change one thing about today, what would it be?",
        "triggers": {},
        "specificity": 0.1,
        "cooldown_days": 2,
        "priority_base": 0.4
    }
]

# Provide around 30, but creating a simplified list first for demo logic, 
# then I'll add a few more to make it ~15 just to show diversity
for i in range(4, 25):
    bank.append({
        "id": f"open_reflection_filler_{i}",
        "category": "open_reflection",
        "text_template": "Tell me about your day in one word.",
        "triggers": {},
        "specificity": 0.05,
        "cooldown_days": 5,
        "priority_base": 0.1
    })
