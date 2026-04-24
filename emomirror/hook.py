from .features import extract_features
from .ml_engine import StateInferenceEngine
from .osc_bridge import OSCBridge
from .insights import generate_insight

def on_new_data(data_dir, parsed_files):
    """
    Hook called by watcher.py when new files are downloaded and parsed.
    """
    print(f"EmoMirror: Processing {len(parsed_files)} new files from {data_dir}")
    
    # Init OSC Client
    osc = OSCBridge()
    osc.send_mode("awakening")
    
    # 1. Extract Features
    features = extract_features(parsed_files)
    print(f"Extracted features: {features}")
    
    # 2. State Inference
    engine = StateInferenceEngine()
    state, intensity, deviations = engine.infer_state(features)
    
    print(f"Inferred State: {state} (Intensity: {intensity:.2f})")
    print(f"Deviations: {deviations}")
    
    # 3. Generate Insight
    insight = generate_insight(state, features)
    print(f"Insight: {insight}")
    
    # 4. Send to TouchDesigner
    osc.send_state(state, intensity, features, deviations)
    osc.send_insight(insight)
    
    # Once state is sent, transition to live mirror mode
    osc.send_mode("live")
    print("EmoMirror pipeline finished.")
