import time
import threading
from pythonosc import dispatcher, osc_server
from .osc_bridge import OSCBridge
from .config import POPULATION_BASELINE

class BiofeedbackGame:
    def __init__(self, baseline=None):
        self.baseline = baseline or POPULATION_BASELINE
        self.osc_out = OSCBridge()
        
        # Real-time state
        self.current_hr = self.baseline["hr_mean"]
        self.current_eda = self.baseline["eda_mean"]
        self.current_motion = 0.0
        
        # History for trend analysis
        self.hr_history = []
        self.eda_history = []
        
        # Game state
        self.is_active = False
        self.progress = 0.0
        
        # Setup OSC Server to listen to EmotiBit Oscilloscope
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/HR", self._hr_handler)
        self.dispatcher.map("/EmotiBit/0/EA", self._eda_handler)
        self.dispatcher.map("/EmotiBit/0/AX", self._motion_handler) # Simplification
        
    def _hr_handler(self, address, *args):
        if args:
            self.current_hr = args[0]
            self.hr_history.append(self.current_hr)
            if len(self.hr_history) > 10: self.hr_history.pop(0)

    def _eda_handler(self, address, *args):
        if args:
            self.current_eda = args[0]
            self.eda_history.append(self.current_eda)
            if len(self.eda_history) > 10: self.eda_history.pop(0)

    def _motion_handler(self, address, *args):
        if args:
            self.current_motion = abs(args[0])

    def start_game(self, duration_seconds=180):
        """Starts the biofeedback interactive game loop."""
        print("Starting Biofeedback Game...")
        self.is_active = True
        self.progress = 0.0
        self.osc_out.client.send_message("/emo/biofeedback/active", 1)
        
        # Start OSC Server in a background thread
        server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 12345), self.dispatcher)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        start_time = time.time()
        
        while self.is_active and (time.time() - start_time) < duration_seconds:
            self._update_game_logic()
            time.sleep(0.5) # 2 Hz update rate
            
        print("Biofeedback Game Ended.")
        self.is_active = False
        self.osc_out.client.send_message("/emo/biofeedback/active", 0)
        server.shutdown()

    def _update_game_logic(self):
        """Calculates progress and generates interactive instructions."""
        # 1. Calculate Progress (0.0 to 1.0)
        # Goal: Bring HR and EDA down to baseline, minimize motion
        hr_diff = max(0, self.current_hr - self.baseline["hr_mean"])
        eda_diff = max(0, self.current_eda - self.baseline["eda_mean"])
        
        # Map differences to a 0-1 scale (1 is perfect baseline)
        hr_score = max(0.0, 1.0 - (hr_diff / (2 * self.baseline["hr_std"])))
        eda_score = max(0.0, 1.0 - (eda_diff / (2 * self.baseline["eda_std"])))
        motion_score = max(0.0, 1.0 - min(self.current_motion, 1.0)) # Assuming motion > 1 is bad
        
        # Overall progress
        current_score = (0.4 * hr_score) + (0.4 * eda_score) + (0.2 * motion_score)
        
        # Smooth progress (prevent jumping)
        self.progress = (self.progress * 0.8) + (current_score * 0.2)
        
        # 2. Analyze Trends (Is the user doing the right thing?)
        hr_trend = 0
        if len(self.hr_history) >= 2:
            hr_trend = self.hr_history[-1] - self.hr_history[0] # negative means dropping (good)
            
        # 3. Generate Interactive Instruction
        instruction = "Breathe slowly and find your center."
        
        if self.current_motion > 0.5:
            instruction = "Try to soften your posture and sit completely still."
        elif hr_trend > 2.0: # HR is going up!
            instruction = "Inhale deeply... and exhale slowly. Let it go."
        elif hr_trend < -1.0: # HR is dropping!
            instruction = "You are doing great. Keep that slow rhythm."
        elif self.progress > 0.8:
            instruction = "Perfect. Hold this calm state."
            
        # 4. Send to TouchDesigner
        self.osc_out.client.send_message("/emo/biofeedback/progress", float(self.progress))
        self.osc_out.client.send_message("/emo/biofeedback/instruction", instruction)
        
        # Also send raw data so TD can show live numbers
        self.osc_out.client.send_message("/emo/hr/current", float(self.current_hr))
        self.osc_out.client.send_message("/emo/eda/current", float(self.current_eda))

if __name__ == "__main__":
    # Standalone test
    game = BiofeedbackGame()
    game.start_game(duration_seconds=60)
