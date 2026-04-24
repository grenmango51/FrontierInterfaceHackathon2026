from pythonosc import udp_client
from .config import OSC_IP, OSC_PORT_OUT

# Color mapping for states (R, G, B)
STATE_COLORS = {
    "calm": (0.0, 0.5, 0.8),         # Blue/Teal
    "stressed": (1.0, 0.4, 0.0),     # Orange
    "anxious": (1.0, 0.8, 0.0),      # Yellow-Orange
    "active": (0.0, 1.0, 0.5),       # Green/Cyan
    "fatigued": (0.4, 0.4, 0.6),     # Muted Purple
    "overstimulated": (1.0, 0.0, 0.5) # Hot Pink
}

class OSCBridge:
    def __init__(self):
        self.client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT_OUT)

    def send_mode(self, mode_string):
        """Sends the current operating mode of the mirror."""
        self.client.send_message("/emo/mode", mode_string)

    def send_state(self, state_name, intensity, features, deviations):
        """
        Sends the full state package to TouchDesigner.
        """
        # State & Intensity
        self.client.send_message("/emo/state/current", state_name)
        self.client.send_message("/emo/state/intensity", float(intensity))
        
        # Glitch factor (higher if stressed/overstimulated)
        glitch = 0.0
        if state_name in ["stressed", "overstimulated"]:
            glitch = min(intensity * 1.5, 1.0)
        elif state_name == "anxious":
            glitch = min(intensity * 0.5, 0.5)
        self.client.send_message("/emo/state/glitch", float(glitch))
        
        # Color
        color = STATE_COLORS.get(state_name, (1.0, 1.0, 1.0))
        self.client.send_message("/emo/state/color/r", float(color[0]))
        self.client.send_message("/emo/state/color/g", float(color[1]))
        self.client.send_message("/emo/state/color/b", float(color[2]))
        
        # Metrics
        if features.get("hr_mean") is not None:
            self.client.send_message("/emo/hr/current", float(features["hr_mean"]))
        self.client.send_message("/emo/hr/deviation", float(deviations.get("hr", 0.0)))
        
        if features.get("eda_mean") is not None:
            self.client.send_message("/emo/eda/current", float(features["eda_mean"]))
        self.client.send_message("/emo/eda/deviation", float(deviations.get("eda", 0.0)))
        
        if features.get("activity_mean") is not None:
            self.client.send_message("/emo/motion/level", float(features["activity_mean"]))
            
        if features.get("temp_mean") is not None:
            self.client.send_message("/emo/temp/current", float(features["temp_mean"]))

    def send_insight(self, insight_text):
        """Sends a text insight to display."""
        self.client.send_message("/emo/insight", insight_text)
