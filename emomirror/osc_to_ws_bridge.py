"""
OSC → WebSocket bridge for EmoMirror biofeedback challenge.

Listens for EmotiBit Oscilloscope OSC output on UDP :12345
Re-emits HR samples and raw PPG:GRN as JSON over WebSocket :8765.

Usage:
    pip install python-osc websockets
    python emomirror/osc_to_ws_bridge.py

Messages sent to browser:
    {"hr": 72.5}              — processed HR at ~1Hz
    {"ppg": 12345.6}          — raw PPG green channel at ~25Hz
"""

import asyncio
import json
import threading
from pythonosc import dispatcher, osc_server
import websockets

OSC_IP   = "0.0.0.0"
OSC_PORT = 12345
WS_PORT  = 8765

_connected_clients = set()
_loop = None  # asyncio event loop (set in ws server thread)

# ── WebSocket server ─────────────────────────────────────────────────────────

async def _ws_handler(websocket):
    _connected_clients.add(websocket)
    print(f"[bridge] Browser connected ({len(_connected_clients)} clients)")
    try:
        await websocket.wait_closed()
    finally:
        _connected_clients.discard(websocket)
        print(f"[bridge] Browser disconnected ({len(_connected_clients)} clients)")

async def _start_ws():
    global _loop
    _loop = asyncio.get_running_loop()
    async with websockets.serve(_ws_handler, "localhost", WS_PORT):
        print(f"[bridge] WebSocket server listening on ws://localhost:{WS_PORT}")
        await asyncio.Future()  # run forever

def _run_ws():
    asyncio.run(_start_ws())

# ── Broadcast helper ─────────────────────────────────────────────────────────

def _broadcast(payload: str):
    if _loop is None or not _connected_clients:
        return

    async def _send():
        dead = set()
        for ws in list(_connected_clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.add(ws)
        _connected_clients.difference_update(dead)

    asyncio.run_coroutine_threadsafe(_send(), _loop)

# ── OSC handlers ─────────────────────────────────────────────────────────────

def _on_hr(address, *args):
    if not args:
        return
    hr = float(args[0])
    _broadcast(json.dumps({"hr": round(hr, 2)}))

def _on_ppg(address, *args):
    """Forward raw PPG green channel at ~25Hz for per-beat HR computation."""
    if not args:
        return
    ppg = float(args[0])
    _broadcast(json.dumps({"ppg": round(ppg, 4)}))

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=_run_ws, daemon=True)
    ws_thread.start()

    # Start OSC server (blocking, on main thread)
    d = dispatcher.Dispatcher()
    d.map("/EmotiBit/0/HR",      _on_hr)
    d.map("/EmotiBit/0/PPG:GRN", _on_ppg)

    server = osc_server.ThreadingOSCUDPServer((OSC_IP, OSC_PORT), d)
    print(f"[bridge] OSC server listening on udp://{OSC_IP}:{OSC_PORT}")
    print(f"[bridge] Forwarding /EmotiBit/0/HR      → ws://localhost:{WS_PORT}")
    print(f"[bridge] Forwarding /EmotiBit/0/PPG:GRN → ws://localhost:{WS_PORT}")
    print("[bridge] Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bridge] Stopped.")

if __name__ == "__main__":
    main()
