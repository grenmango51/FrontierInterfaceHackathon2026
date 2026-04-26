// biosignal.js — hardware-agnostic HR data source
// Live mode:  connects to ws://localhost:8765 (fed by emomirror/osc_to_ws_bridge.py)
//             Receives both {"hr": value} at ~1Hz AND {"ppg": value} at ~25Hz.
//             Per-beat HR is derived from PPG peaks (inter-beat intervals) for
//             high-frequency RSA computation. Falls back to raw HR if no PPG.
// Mock mode:  generates synthetic HR curve for demo/dev
//
// API:
//   biosignalSource.subscribe(fn)      — fn({ hr, timestamp }) called on each beat or ~1Hz
//   biosignalSource.unsubscribe(fn)
//   biosignalSource.setMode('live'|'mock')
//   biosignalSource.setMockProfile('success'|'struggle'|'realistic')
//   biosignalSource.getBaseline()      — returns rolling 60s baseline avg HR

const biosignalSource = (() => {
    const WS_URL = 'ws://localhost:8765';
    const BASELINE_WINDOW_MS = 60_000;

    let _mode = 'live';
    let _profile = 'realistic';
    let _listeners = [];
    let _ws = null;
    let _mockTimer = null;
    let _mockTime = 0;
    let _hrHistory = []; // { hr, timestamp }

    // ── PPG peak detector ────────────────────────────────────────────────────
    // Detects peaks in the green PPG channel (25Hz) to compute instantaneous HR.
    // Algorithm: adaptive threshold based on recent signal range,
    // refractory period of 300ms to suppress double-detection.

    const PPG_SAMPLE_RATE   = 25;   // Hz
    const PPG_BUFFER_SIZE   = 75;   // 3 seconds of history for threshold estimation
    const PPG_REFRACTORY_MS = 350;  // minimum time between detected beats (max ~170 bpm)
    const PPG_MIN_IBI_MS    = 350;  // ignore IBIs shorter than this (noise)
    const PPG_MAX_IBI_MS    = 1500; // ignore IBIs longer than this (~40 bpm floor)

    let _ppgBuf       = [];   // ring buffer of recent PPG values
    let _ppgPrev      = 0;    // previous sample for slope detection
    let _ppgPrev2     = 0;    // two samples ago
    let _lastBeatTs   = 0;    // timestamp of last confirmed beat
    let _ibiHistory   = [];   // last 8 inter-beat intervals (ms)
    let _ppgHasFired  = false;// true once we've received at least one PPG sample

    function _processPPG(value) {
        const now = Date.now();
        _ppgHasFired = true;

        // Update ring buffer
        _ppgBuf.push(value);
        if (_ppgBuf.length > PPG_BUFFER_SIZE) _ppgBuf.shift();

        // Need at least 3 samples to detect a local maximum
        if (_ppgBuf.length < 3) {
            _ppgPrev2 = _ppgPrev;
            _ppgPrev  = value;
            return;
        }

        // Adaptive threshold: 60% of range within the buffer window
        const min = Math.min(..._ppgBuf);
        const max = Math.max(..._ppgBuf);
        const range = max - min;
        const threshold = min + range * 0.60;

        // Local maximum detection: prev2 < prev > current AND prev > threshold
        const isLocalMax = (_ppgPrev > _ppgPrev2) && (_ppgPrev > value) && (_ppgPrev > threshold);

        if (isLocalMax) {
            const timeSinceLast = now - _lastBeatTs;
            if (timeSinceLast >= PPG_REFRACTORY_MS) {
                // Valid beat detected
                if (_lastBeatTs > 0) {
                    const ibi = timeSinceLast; // inter-beat interval in ms
                    if (ibi >= PPG_MIN_IBI_MS && ibi <= PPG_MAX_IBI_MS) {
                        _ibiHistory.push(ibi);
                        if (_ibiHistory.length > 3) _ibiHistory.shift();

                        // Median-of-3 guard: detect single-beat spikes/dropouts
                        let targetIbi = ibi;
                        if (_ibiHistory.length === 3) {
                            const sorted = [..._ibiHistory].sort((a, b) => a - b);
                            const median = sorted[1];
                            // If new IBI deviates > 30% from median, it's likely a misfire
                            if (Math.abs(ibi - median) > median * 0.3) {
                                targetIbi = median;
                            }
                        }

                        // Emit instantaneous HR from the guarded IBI.
                        // Smoothing for RSA computation is handled downstream in the challenge engine.
                        const hr = 60000 / targetIbi;
                        _emit({ hr: Math.round(hr * 10) / 10, timestamp: now });
                    }
                }
                _lastBeatTs = now;
            }
        }

        _ppgPrev2 = _ppgPrev;
        _ppgPrev  = value;
    }

    // ── emit to all subscribers ──────────────────────────────────────────────
    function _emit(sample) {
        _hrHistory.push(sample);
        const cutoff = sample.timestamp - BASELINE_WINDOW_MS;
        _hrHistory = _hrHistory.filter(s => s.timestamp >= cutoff);
        _listeners.forEach(fn => fn(sample));
    }

    // ── mock profiles ────────────────────────────────────────────────────────
    // Each profile simulates a different user response to box breathing.
    // Base HR ~80, target is roughly −5 bpm swing growth.
    function _mockSample() {
        _mockTime += 1;
        const t = _mockTime;
        let hr;

        if (_profile === 'success') {
            // Swing builds from ~3 bpm → ~13 bpm over 90s, simulating real RSA improvement
            const trend    = Math.max(62, 80 - t * 0.2);
            const oscAmp   = Math.min(13, 3 + t * 0.11); // grows over time
            const osc      = oscAmp * Math.sin(t * (2 * Math.PI / 16));
            hr = trend + osc + (Math.random() - 0.5) * 1.5;
        } else if (_profile === 'struggle') {
            // Swing stays small (~3–6 bpm), never quite reaches target
            const trend    = Math.max(74, 88 - t * 0.05);
            const oscAmp   = Math.min(6, 2 + t * 0.04);
            const osc      = oscAmp * Math.sin(t * (2 * Math.PI / 16));
            hr = trend + osc + (Math.random() - 0.5) * 4;
        } else {
            // realistic: swing builds from ~2 bpm → ~10 bpm over ~120s
            const trend    = Math.max(65, 80 - t * 0.15);
            const oscAmp   = Math.min(10, 2 + t * 0.07);
            const osc      = oscAmp * Math.sin(t * (2 * Math.PI / 16));
            hr = trend + osc + (Math.random() - 0.5) * 2.5;
        }

        _emit({ hr: Math.round(hr * 10) / 10, timestamp: Date.now() });
    }

    function _startMock() {
        _stopMock();
        _mockTime = 0;
        _mockTimer = setInterval(_mockSample, 1000);
    }

    function _stopMock() {
        if (_mockTimer) { clearInterval(_mockTimer); _mockTimer = null; }
    }

    // ── live WebSocket ───────────────────────────────────────────────────────
    function _startLive() {
        _stopLive();
        // Reset PPG detector state
        _ppgBuf = []; _ppgPrev = 0; _ppgPrev2 = 0;
        _lastBeatTs = 0; _ibiHistory = []; _ppgHasFired = false;

        // Fallback to raw HR if no PPG beats arrive within 5 seconds
        let _ppgFallbackTimer = setTimeout(() => {
            if (!_ppgHasFired) {
                console.warn('[biosignal] No PPG data received — using raw HR at 1Hz');
            }
        }, 5000);

        try {
            _ws = new WebSocket(WS_URL);
            _ws.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.ppg != null) {
                        // High-frequency PPG: derive per-beat HR
                        _processPPG(parseFloat(msg.ppg));
                    } else if (msg.hr != null && !_ppgHasFired) {
                        // Fallback: use raw 1Hz HR if PPG not flowing
                        _emit({ hr: parseFloat(msg.hr), timestamp: Date.now() });
                    }
                } catch (_) {}
            };
            _ws.onerror = () => {
                clearTimeout(_ppgFallbackTimer);
                console.warn('[biosignal] WebSocket error — falling back to mock');
                _stopLive();
                _startMock();
            };
            _ws.onclose = () => {
                clearTimeout(_ppgFallbackTimer);
                console.warn('[biosignal] WebSocket closed — falling back to mock');
                _startMock();
            };
        } catch (e) {
            console.warn('[biosignal] WebSocket unavailable — using mock', e);
            _startMock();
        }
    }

    function _stopLive() {
        if (_ws) { _ws.close(); _ws = null; }
    }

    // ── public API ───────────────────────────────────────────────────────────
    return {
        subscribe(fn) {
            _listeners.push(fn);
            if (_listeners.length === 1) {
                // First subscriber — start the source
                _mode === 'live' ? _startLive() : _startMock();
            }
        },

        unsubscribe(fn) {
            _listeners = _listeners.filter(l => l !== fn);
            if (_listeners.length === 0) {
                _stopMock();
                _stopLive();
            }
        },

        setMode(mode) {
            _mode = mode;
            if (_listeners.length > 0) {
                _stopMock();
                _stopLive();
                mode === 'live' ? _startLive() : _startMock();
            }
        },

        setMockProfile(profile) {
            _profile = profile;
        },

        // Rolling 60s average HR (used to set challenge baseline)
        getBaseline() {
            if (_hrHistory.length === 0) return null;
            const sum = _hrHistory.reduce((a, s) => a + s.hr, 0);
            return sum / _hrHistory.length;
        },

        // Full history for RSA computation (last 60s)
        getHistory() {
            return [..._hrHistory];
        },
    };
})();
