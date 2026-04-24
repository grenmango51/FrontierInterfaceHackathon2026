import json
from pathlib import Path
from .config import DATA_DIR

class PreferenceSimulator:
    def __init__(self, user_id="default_user"):
        self.user_dir = DATA_DIR / user_id
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.pref_file = self.user_dir / "preferences.json"
        
        # Default scores if no file exists
        self.scores = {
            "overstimulated": {"Decompress": 1, "Gentle Focus": 1, "Stay Active": 1},
            "stressed": {"Unwind": 1, "Sound Bath": 1, "Gentle Walk": 1},
            "anxious": {"Breathe": 1, "Calm Reading": 1, "Nature Sounds": 1},
            "fatigued": {"Rest Mode": 1, "Gentle Energize": 1, "Recovery": 1}
        }
        self._load()

    def _load(self):
        if self.pref_file.exists():
            try:
                with open(self.pref_file, "r") as f:
                    saved_scores = json.load(f)
                    # Merge to ensure we don't lose default states if file is old
                    for state, options in saved_scores.items():
                        if state in self.scores:
                            self.scores[state].update(options)
            except Exception as e:
                print(f"Error loading preferences: {e}")

    def _save(self):
        try:
            with open(self.pref_file, "w") as f:
                json.dump(self.scores, f, indent=4)
        except Exception as e:
            print(f"Error saving preferences: {e}")

    def log_choice(self, state, chosen_option):
        """
        Increases the score of the chosen option for a given state.
        This SIMULATES preference learning.
        """
        state = state.lower()
        if state in self.scores and chosen_option in self.scores[state]:
            self.scores[state][chosen_option] += 1
            print(f"Logged preference: +1 for '{chosen_option}' in state '{state}'")
            self._save()

    def get_ordered_options(self, state):
        """
        Returns the options for a state, ordered by highest score first.
        """
        state = state.lower()
        if state not in self.scores:
            return []
            
        # Sort options by score descending
        options = self.scores[state]
        sorted_options = sorted(options.items(), key=lambda item: item[1], reverse=True)
        
        # Return just the names
        return [opt[0] for opt in sorted_options]

# Standalone test
if __name__ == "__main__":
    pref = PreferenceSimulator()
    print("Initial order for stressed:", pref.get_ordered_options("stressed"))
    pref.log_choice("stressed", "Sound Bath")
    pref.log_choice("stressed", "Sound Bath")
    print("New order for stressed:", pref.get_ordered_options("stressed"))
