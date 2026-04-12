"""
ABB ACS180 – Web Control Panel (Flask)
=======================================
Runs a local web server with a control dashboard.
Usage:
    python web_app.py              # Real drive mode (default)
    python web_app.py --sim        # Simulator mode
"""

import argparse
import atexit
import json
import signal
import socket
import threading
import time
from flask import Flask, render_template_string, jsonify, request
from abb_driver import MockABBDrive, RealABBDrive
import config

app = Flask(__name__)
drive = None  # Will be set in main
startup_error = None
drive_connected = False
demo_lock = threading.Lock()
demo_stop_event = threading.Event()
demo_active = False
demo_name = ""
shutdown_done = False


def _is_port_in_use(host: str, port: int) -> bool:
    """Return True if TCP host:port is already occupied by another process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.connect_ex((host, port)) == 0


def _safe_shutdown() -> None:
    """Best-effort shutdown to release COM/Modbus resources on exit."""
    global shutdown_done, demo_active, demo_name
    if shutdown_done:
        return
    shutdown_done = True

    try:
        demo_stop_event.set()
        with demo_lock:
            demo_active = False
            demo_name = ""
    except Exception:
        pass

    try:
        if drive is not None:
            drive.stop()
    except Exception:
        pass

    try:
        if drive is not None:
            drive.disconnect()
    except Exception:
        pass


def _signal_shutdown(signum, _frame) -> None:
    print(f"\n[SHUTDOWN] Signal {signum} received. Closing app cleanly...")
    _safe_shutdown()
    raise SystemExit(0)

# ══════════════════════════════════════════════
# HTML Template
# ══════════════════════════════════════════════

HTML_PAGE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABB ACS180 Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        h1 {
            color: #00d4ff;
            margin-bottom: 5px;
            font-size: 1.8em;
        }
        .subtitle {
            color: #888;
            margin-bottom: 25px;
            font-size: 0.9em;
        }
        .mode-badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .mode-sim { background: #ff9800; color: #000; }
        .mode-real { background: #f44336; color: #fff; }
        .conn-banner {
            width: 100%;
            max-width: 800px;
            margin-bottom: 18px;
            padding: 12px 14px;
            border-radius: 10px;
            font-size: 0.95em;
            border: 1px solid;
        }
        .conn-ok {
            background: #17331d;
            color: #8de39a;
            border-color: #2e7d32;
        }
        .conn-err {
            background: #3a1b1b;
            color: #ffb3b3;
            border-color: #f44336;
        }

        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 800px;
            width: 100%;
        }

        .panel {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #0f3460;
        }
        .panel h2 {
            color: #00d4ff;
            font-size: 1.1em;
            margin-bottom: 15px;
            border-bottom: 1px solid #0f3460;
            padding-bottom: 8px;
        }

        /* Status Panel */
        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .status-item {
            background: #0f3460;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .status-item .label {
            font-size: 0.75em;
            color: #888;
            margin-bottom: 4px;
        }
        .status-item .value {
            font-size: 1.4em;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        }
        .status-item.full-width {
            grid-column: 1 / -1;
        }

        /* Indicators */
        .indicators {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .indicator {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            border: 2px solid;
        }
        .ind-off { border-color: #333; color: #555; background: #1a1a2e; }
        .ind-green { border-color: #4caf50; color: #4caf50; background: #1b3a1b; }
        .ind-red { border-color: #f44336; color: #f44336; background: #3a1b1b; }
        .ind-orange { border-color: #ff9800; color: #ff9800; background: #3a2e1b; }
        .ind-blue { border-color: #2196f3; color: #2196f3; background: #1b2a3a; }

        /* Buttons */
        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .btn {
            padding: 14px 10px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
            color: #fff;
        }
        .btn:hover { transform: scale(1.03); filter: brightness(1.2); }
        .btn:active { transform: scale(0.97); }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .btn-start { background: #4caf50; }
        .btn-stop { background: #ff9800; }
        .btn-emergency { background: #f44336; grid-column: 1 / -1; }
        .btn-reset { background: #9c27b0; }
        .btn-fault-sim { background: #795548; }
        .btn-demo { background: #009688; }
        .btn-demo.active { background: #c62828; }

        /* Speed Control */
        .speed-control {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .speed-slider-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .speed-slider-row input[type="range"] {
            flex: 1;
            height: 8px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 4px;
            outline: none;
        }
        .speed-slider-row input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 22px;
            height: 22px;
            background: #00d4ff;
            border-radius: 50%;
            cursor: pointer;
        }
        .speed-value {
            font-size: 1.4em;
            font-weight: bold;
            font-family: 'Consolas', monospace;
            color: #00d4ff;
            min-width: 70px;
            text-align: left;
        }
        .speed-presets {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .speed-presets button {
            padding: 6px 14px;
            border: 1px solid #0f3460;
            background: #16213e;
            color: #00d4ff;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85em;
        }
        .speed-presets button:hover { background: #0f3460; }
        .btn-set-speed {
            background: #2196f3;
            padding: 10px;
            border: none;
            border-radius: 8px;
            color: #fff;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
        }
        .btn-set-speed:hover { filter: brightness(1.2); }

        /* Log */
        .log-panel { grid-column: 1 / -1; }
        #log {
            background: #0a0a1a;
            border-radius: 8px;
            padding: 12px;
            height: 150px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 0.82em;
            line-height: 1.6;
            direction: ltr;
            text-align: left;
        }
        .log-ok { color: #4caf50; }
        .log-err { color: #f44336; }
        .log-cmd { color: #00d4ff; }
        .log-info { color: #888; }

        /* Params panel */
        .params-panel { grid-column: 1 / -1; }
        .btn-toggle-params {
            background: #0f3460;
            border: 1px solid #00d4ff;
            color: #00d4ff;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .btn-toggle-params:hover { background: #16213e; filter: brightness(1.3); }
        #params-table {
            display: none;
            width: 100%;
            border-collapse: collapse;
            font-family: 'Consolas', monospace;
            font-size: 0.82em;
            direction: ltr;
            text-align: left;
        }
        #params-table th {
            background: #0f3460;
            padding: 6px 10px;
            color: #00d4ff;
            text-align: left;
        }
        #params-table td {
            padding: 5px 10px;
            border-bottom: 1px solid #0f3460;
        }
        #params-table tr:hover { background: #0f3460; }

        /* Direction button */
        .btn-reverse { background: #607d8b; }
        .btn-reverse.active { background: #e91e63; }

        @media (max-width: 700px) {
            .dashboard { grid-template-columns: 1fr; }
            .log-panel, .params-panel { grid-column: 1; }
        }
    </style>
</head>
<body>
    <h1>⚡ ABB ACS180 Control Panel</h1>
    <div class="subtitle">ACS180-04S-07A8 | Siemens 0.25kW | Delta 230V</div>
    <span class="mode-badge {{ 'mode-sim' if mode == 'SIMULATOR' else 'mode-real' }}">{{ mode }}</span>
    <div class="conn-banner {{ 'conn-ok' if drive_connected else 'conn-err' }}">
        {{ connection_message }}
    </div>

    <div class="dashboard">
        <!-- Status Panel -->
        <div class="panel">
            <h2>📊 סטטוס</h2>
            <div class="status-grid">
                <div class="status-item">
                    <div class="label">תדר</div>
                    <div class="value" id="freq-hz">-- Hz</div>
                </div>
                <div class="status-item">
                    <div class="label">מהירות</div>
                    <div class="value" id="speed-rpm">-- RPM</div>
                </div>
                <div class="status-item">
                    <div class="label">זרם</div>
                    <div class="value" id="current">-- A</div>
                </div>
                <div class="status-item">
                    <div class="label">אחוז</div>
                    <div class="value" id="speed-pct">-- %</div>
                </div>
                <div class="status-item">
                    <div class="label">Status Word</div>
                    <div class="value" id="status-word">--</div>
                </div>
            </div>
            <div class="indicators" id="indicators">
                <span class="indicator ind-off" id="ind-ready">READY</span>
                <span class="indicator ind-off" id="ind-running">RUNNING</span>
                <span class="indicator ind-off" id="ind-fault">FAULT</span>
                <span class="indicator ind-off" id="ind-warning">WARNING</span>
            </div>
        </div>

        <!-- Control Buttons -->
        <div class="panel">
            <h2>🎮 שליטה</h2>
            <div class="btn-group">
                <button class="btn btn-start manual-control" onclick="sendCmd('start')">▶ START</button>
                <button class="btn btn-stop manual-control" onclick="sendCmd('stop')">⏹ STOP</button>
                <button class="btn btn-reverse manual-control" id="btn-reverse" onclick="toggleDirection()">🔄 קדימה</button>
                <button class="btn btn-reset manual-control" onclick="sendCmd('fault_reset')">🔧 FAULT RESET</button>
                <button class="btn btn-demo" id="btn-demo" onclick="toggleDemo()">🎬 DEMO</button>
                <button class="btn btn-fault-sim" onclick="sendCmd('sim_fault')" id="btn-sim-fault" style="{{ '' if mode == 'SIMULATOR' else 'display:none' }}">⚡ SIM FAULT</button>
                <button class="btn btn-emergency" onclick="if(confirm('Emergency Stop?')) sendCmd('emergency_stop')">🚨 EMERGENCY STOP</button>
            </div>
        </div>

        <!-- Speed Control -->
        <div class="panel" style="grid-column: 1 / -1;">
            <h2>🔧 מהירות</h2>
            <div class="speed-control">
                <div class="speed-slider-row">
                    <input type="range" id="speed-slider" min="0" max="100" step="0.5" value="0"
                              oninput="onSliderInput(this.value)" class="manual-control">
                    <span class="speed-value" id="speed-display">0%</span>
                </div>
                <div class="speed-presets">
                    <button onclick="setSlider(0)">0%</button>
                    <button onclick="setSlider(10)">10%</button>
                    <button onclick="setSlider(25)">25%</button>
                    <button onclick="setSlider(50)">50%</button>
                    <button onclick="setSlider(75)">75%</button>
                    <button onclick="setSlider(100)">100%</button>
                </div>
                <div style="font-size:0.8em;color:#888;text-align:center;">גרור את הסליידר - המהירות מתעדכנת בזמן אמת</div>
            </div>
        </div>

        <!-- Parameters Panel -->
        <div class="panel params-panel">
            <h2>⚙️ פרמטרים</h2>
            <button class="btn-toggle-params" onclick="toggleParams()">📋 הצג פרמטרים</button>
            <table id="params-table">
                <thead><tr><th>Parameter</th><th>Value</th><th>Description</th></tr></thead>
                <tbody id="params-body"></tbody>
            </table>
        </div>

        <!-- Log -->
        <div class="panel log-panel">
            <h2>📋 לוג</h2>
            <div id="log"></div>
        </div>
    </div>

    <script>
        const logEl = document.getElementById('log');
        let isReversed = false;
        let isRunning = false;
        let demoActive = false;

        function addLog(msg, cls = 'log-info') {
            const time = new Date().toLocaleTimeString();
            logEl.innerHTML += `<div class="${cls}">[${time}] ${msg}</div>`;
            logEl.scrollTop = logEl.scrollHeight;
        }

        async function sendCmd(action) {
            addLog(`Sending: ${action}`, 'log-cmd');
            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: action})
                });
                const data = await resp.json();
                if (data.ok) {
                    addLog(data.msg, 'log-ok');
                } else {
                    addLog('ERROR: ' + data.msg, 'log-err');
                }
                refreshStatus();
            } catch(e) {
                addLog('Connection error: ' + e, 'log-err');
            }
        }

        async function toggleDirection() {
            if (demoActive) {
                addLog('ERROR: DEMO פעיל, שליטה ידנית חסומה', 'log-err');
                return;
            }
            if (isRunning) {
                addLog('ERROR: עצור את המנוע לפני היפוך כיוון!', 'log-err');
                return;
            }
            const newDir = !isReversed;
            addLog(`Setting direction: ${newDir ? 'REVERSE' : 'FORWARD'}`, 'log-cmd');
            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: 'set_direction', reverse: newDir})
                });
                const data = await resp.json();
                if (data.ok) {
                    isReversed = newDir;
                    updateDirectionBtn();
                    addLog(data.msg, 'log-ok');
                } else {
                    addLog('ERROR: ' + data.msg, 'log-err');
                }
            } catch(e) {
                addLog('Connection error: ' + e, 'log-err');
            }
        }

        function updateDirectionBtn() {
            const btn = document.getElementById('btn-reverse');
            if (isReversed) {
                btn.textContent = '🔄 אחורה';
                btn.classList.add('active');
            } else {
                btn.textContent = '🔄 קדימה';
                btn.classList.remove('active');
            }
            btn.disabled = isRunning || demoActive;
        }

        function updateDemoBtn() {
            const btn = document.getElementById('btn-demo');
            btn.textContent = demoActive ? '⏹ עצור DEMO' : '🎬 DEMO';
            btn.classList.toggle('active', demoActive);

            document.querySelectorAll('.manual-control').forEach(el => {
                if (el.id === 'btn-demo') return;
                el.disabled = demoActive;
            });
        }

        async function toggleDemo() {
            const action = demoActive ? 'stop_demo' : 'run_demo';
            addLog((demoActive ? 'Stopping' : 'Starting') + ' demo...', 'log-cmd');
            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action})
                });
                const data = await resp.json();
                if (data.ok) {
                    addLog(data.msg, 'log-ok');
                } else {
                    addLog('ERROR: ' + data.msg, 'log-err');
                }
                refreshStatus();
            } catch(e) {
                addLog('Connection error: ' + e, 'log-err');
            }
        }

        let paramsVisible = false;
        async function toggleParams() {
            const table = document.getElementById('params-table');
            if (paramsVisible) {
                table.style.display = 'none';
                paramsVisible = false;
                return;
            }
            addLog('Loading parameters...', 'log-cmd');
            try {
                const resp = await fetch('/api/params');
                const data = await resp.json();
                if (!data.ok) { addLog('ERROR: ' + data.msg, 'log-err'); return; }
                const tbody = document.getElementById('params-body');
                tbody.innerHTML = '';
                data.params.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td style="color:#00d4ff">${p.param}</td><td style="font-weight:bold">${p.value !== null ? p.value : 'N/A'}</td><td style="color:#888">${p.desc}</td>`;
                    tbody.appendChild(tr);
                });
                table.style.display = 'table';
                paramsVisible = true;
                addLog(`Loaded ${data.params.length} parameters`, 'log-ok');
            } catch(e) {
                addLog('Connection error: ' + e, 'log-err');
            }
        }

        let speedTimeout = null;

        function onSliderInput(val) {
            document.getElementById('speed-display').textContent = val + '%';
            // Debounce: send speed after 150ms of no movement
            clearTimeout(speedTimeout);
            speedTimeout = setTimeout(() => setSpeed(parseFloat(val)), 150);
        }

        function setSlider(val) {
            document.getElementById('speed-slider').value = val;
            document.getElementById('speed-display').textContent = val + '%';
            setSpeed(val);
        }

        async function setSpeed(pct) {
            if (demoActive) {
                addLog('ERROR: DEMO פעיל, שליטה ידנית חסומה', 'log-err');
                return;
            }
            try {
                const resp = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: 'set_speed', percent: pct})
                });
                const data = await resp.json();
                if (data.ok) {
                    addLog(`Speed: ${pct}%`, 'log-ok');
                } else {
                    addLog('ERROR: ' + data.msg, 'log-err');
                }
                refreshStatus();
            } catch(e) {
                addLog('Connection error: ' + e, 'log-err');
            }
        }

        async function refreshStatus() {
            try {
                const resp = await fetch('/api/status');
                const s = await resp.json();
                if (!s.ok) return;
                const d = s.data;

                document.getElementById('speed-rpm').textContent = d.speed_rpm.toFixed(0) + ' RPM';
                document.getElementById('speed-pct').textContent = d.speed_percent.toFixed(1) + '%';
                document.getElementById('freq-hz').textContent = d.frequency_hz.toFixed(1) + ' Hz';
                document.getElementById('current').textContent = d.current_a.toFixed(2) + ' A';
                document.getElementById('status-word').textContent = d.status_hex;
                demoActive = !!d.demo_active;

                setIndicator('ind-ready', d.ready, 'ind-green');
                setIndicator('ind-running', d.running, 'ind-blue');
                setIndicator('ind-fault', d.fault, 'ind-red');
                setIndicator('ind-warning', d.warning, 'ind-orange');

                isRunning = d.running;
                updateDirectionBtn();
                updateDemoBtn();

                // Visual feedback - change body border when running
                document.body.style.borderTop = d.running ? '4px solid #4caf50' : d.fault ? '4px solid #f44336' : '4px solid #1a1a2e';
            } catch(e) { /* silent */ }
        }

        function setIndicator(id, active, activeClass) {
            const el = document.getElementById(id);
            el.className = 'indicator ' + (active ? activeClass : 'ind-off');
        }

        // Auto-refresh every 1 second
        setInterval(refreshStatus, 1000);
        refreshStatus();
        addLog('Dashboard loaded. Ready.', 'log-info');
    </script>
</body>
</html>
"""


# ══════════════════════════════════════════════
# API Routes
# ══════════════════════════════════════════════

@app.route("/")
def index():
    mode = "SIMULATOR" if isinstance(drive, MockABBDrive) else "REAL DRIVE"
    if isinstance(drive, MockABBDrive):
        connection_message = "Simulator mode active (no hardware control on COM/RS485)."
    elif drive_connected:
        connection_message = f"Drive connection OK on {config.COM_PORT}, slave {config.SLAVE_ID}"
    else:
        connection_message = startup_error or "Drive is not connected. The dashboard is up, but commands will fail until COM connection works."
    return render_template_string(
        HTML_PAGE,
        mode=mode,
        drive_connected=drive_connected,
        connection_message=connection_message,
    )


@app.route("/api/status")
def api_status():
    if not drive_connected:
        return jsonify({"ok": False, "msg": startup_error or "Drive not connected"})
    status = drive.read_status()
    if status is None:
        return jsonify({"ok": False, "msg": "Could not read status"})
    status["demo_active"] = demo_active
    status["demo_name"] = demo_name
    return jsonify({"ok": True, "data": status})


@app.route("/api/params")
def api_params():
    if not drive_connected:
        return jsonify({"ok": False, "msg": startup_error or "Drive not connected"})
    try:
        params = drive.read_params()
        return jsonify({"ok": True, "params": params})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/api/command", methods=["POST"])
def api_command():
    if not drive_connected:
        return jsonify({"ok": False, "msg": startup_error or "Drive not connected"}), 503
    data = request.get_json()
    if not data or "action" not in data:
        return jsonify({"ok": False, "msg": "No action specified"}), 400

    action = data["action"]

    if action == "start":
        ok = drive.start()
        return jsonify({"ok": ok, "msg": "Drive started" if ok else "Start failed"})

    elif action == "stop":
        ok = drive.stop()
        return jsonify({"ok": ok, "msg": "Drive stopped" if ok else "Stop failed"})

    elif action == "emergency_stop":
        ok = drive.emergency_stop()
        return jsonify({"ok": ok, "msg": "Emergency stop sent" if ok else "Emergency stop failed"})

    elif action == "fault_reset":
        ok = drive.fault_reset()
        return jsonify({"ok": ok, "msg": "Fault reset sent" if ok else "Fault reset failed"})

    elif action == "set_speed":
        pct = data.get("percent", 0)
        try:
            pct = float(pct)
        except (ValueError, TypeError):
            return jsonify({"ok": False, "msg": "Invalid speed value"}), 400
        if not (0.0 <= pct <= 100.0):
            return jsonify({"ok": False, "msg": "Speed must be 0-100%"}), 400
        ok = drive.set_speed(pct)
        return jsonify({"ok": ok, "msg": f"Speed set to {pct:.1f}%" if ok else "Set speed failed"})

    elif action == "sim_fault":
        if hasattr(drive, "simulate_fault"):
            drive.simulate_fault()
            return jsonify({"ok": True, "msg": "Simulated fault injected"})
        return jsonify({"ok": False, "msg": "Not in simulator mode"})

    elif action == "set_direction":
        reverse = data.get("reverse", False)
        # Check if drive is running
        status = drive.read_status()
        if status and status.get("running"):
            return jsonify({"ok": False, "msg": "עצור את המנוע לפני היפוך כיוון!"})
        ok = drive.set_direction(reverse)
        direction = "אחורה" if reverse else "קדימה"
        return jsonify({"ok": ok, "msg": f"כיוון: {direction}" if ok else "Direction change failed"})

    elif action == "run_demo":
        ok, msg = start_demo_sequence()
        return jsonify({"ok": ok, "msg": msg})

    elif action == "stop_demo":
        ok, msg = stop_demo_sequence()
        return jsonify({"ok": ok, "msg": msg})

    return jsonify({"ok": False, "msg": f"Unknown action: {action}"}), 400


def _demo_wait(seconds: float) -> bool:
    end_time = time.time() + seconds
    while time.time() < end_time:
        if demo_stop_event.is_set():
            return False
        time.sleep(0.05)
    return True


def _demo_set_running_speed(percent: float) -> bool:
    if demo_stop_event.is_set():
        return False
    if not drive.set_speed(percent):
        return False
    return _demo_wait(0.28)


def _demo_quick_stop_restart(restart_speed: float, hold_s: float = 0.22) -> bool:
    """Fast stop + fast restart pulse during demo."""
    if demo_stop_event.is_set():
        return False
    if not drive.emergency_stop():
        return False
    if not _demo_wait(hold_s):
        return False
    if not drive.start():
        return False
    return _demo_set_running_speed(restart_speed)


def _demo_run_profile(speeds: list[float], fast_stop_at: set[int] | None = None) -> bool:
    """Run profile with optional fast stop/restart pulses by index."""
    pulse_indices = fast_stop_at or set()
    for idx, speed in enumerate(speeds):
        if not _demo_set_running_speed(speed):
            return False
        if idx in pulse_indices:
            restart_speed = max(12.0, speed - 6.0)
            if not _demo_quick_stop_restart(restart_speed):
                return False
    return True


def _run_demo_sequence() -> None:
    global demo_active, demo_name
    try:
        print("[DEMO] Starting servo-style demonstration...")
        drive.stop()
        if not _demo_wait(0.35):
            return

        if not drive.set_direction(False):
            return
        if not drive.start():
            return

        # Forward: rapid ramps + one fast stop/restart pulse
        if not _demo_run_profile([12, 24, 42, 58, 36, 52, 28], fast_stop_at={3}):
            return

        if not drive.stop():
            return
        if not _demo_wait(0.45):
            return

        # Reverse direction demo
        if not drive.set_direction(True):
            return
        if not drive.start():
            return

        # Reverse: varied speeds + one fast stop/restart pulse
        if not _demo_run_profile([16, 34, 50, 30, 56, 22, 40], fast_stop_at={2}):
            return

        if not drive.stop():
            return
        if not _demo_wait(0.4):
            return

        # Back to forward for final fast pulses
        if not drive.set_direction(False):
            return
        if not drive.start():
            return

        if not _demo_run_profile([20, 45, 25, 60, 18], fast_stop_at={1, 3}):
            return

        # Final fast stop and clean finish
        if not drive.emergency_stop():
            return
        if not _demo_wait(0.25):
            return
        if not drive.start():
            return
        if not _demo_set_running_speed(14):
            return
        if not drive.stop():
            return
        if not _demo_wait(0.25):
            return

        print("[DEMO] Demo finished successfully.")
    finally:
        drive.stop()
        drive.set_direction(False)
        with demo_lock:
            demo_active = False
            demo_name = ""
            demo_stop_event.clear()
        print("[DEMO] Demo state cleared.")


def start_demo_sequence() -> tuple[bool, str]:
    global demo_active, demo_name
    with demo_lock:
        if demo_active:
            return False, "DEMO כבר רץ"

        status = drive.read_status()
        if status and status.get("fault"):
            return False, "יש FAULT פעיל. בצע FAULT RESET לפני DEMO"

        demo_active = True
        demo_name = "servo-demo"
        demo_stop_event.clear()

    threading.Thread(target=_run_demo_sequence, daemon=True).start()
    return True, "DEMO servo-style started"


def stop_demo_sequence() -> tuple[bool, str]:
    global demo_active
    with demo_lock:
        if not demo_active:
            return False, "אין DEMO פעיל"
        demo_stop_event.set()

    drive.stop()
    return True, "DEMO stop requested"


# ══════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════

if __name__ == "__main__":
    import webbrowser

    parser = argparse.ArgumentParser(description="ABB ACS180 Web Control Panel")
    parser.add_argument("--sim", action="store_true", help="Use simulator mode instead of real drive")
    parser.add_argument("--port", type=str, default=config.COM_PORT)
    parser.add_argument("--slave", type=int, default=config.SLAVE_ID)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=5000)
    args = parser.parse_args()

    # Ensure we always release COM/serial on normal exit and Ctrl+C.
    atexit.register(_safe_shutdown)
    signal.signal(signal.SIGINT, _signal_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_shutdown)

    if _is_port_in_use(args.host, args.web_port):
        print(
            f"[ERROR] Port {args.web_port} is already in use on {args.host}. "
            "A previous Python dashboard process is probably still running."
        )
        print("[HINT] Close old process first (example: taskkill /F /IM python.exe)")
        raise SystemExit(1)

    if args.sim:
        drive = MockABBDrive()
    else:
        drive = RealABBDrive(port=args.port, slave_id=args.slave)

    if not args.sim:
        for attempt in range(1, 4):
            print(f"[STARTUP] Connecting to drive on {args.port} (attempt {attempt}/3)...")
            if drive.connect():
                drive_connected = True
                startup_error = None
                break
            time.sleep(0.7)

        if not drive_connected:
            startup_error = (
                f"Drive connection failed on {args.port}. Usually this means COM4 is busy, "
                "the USB-RS485 adapter is disconnected, or the drive is powered off."
            )
            print(f"[WARN] {startup_error}")
            print("[WARN] Starting web dashboard anyway.")
    else:
        drive_connected = drive.connect()
        startup_error = None if drive_connected else "Simulator failed to initialize"

    url = f"http://{args.host}:{args.web_port}"
    print(f"\n  >>> Opening browser: {url}")
    print(f"  >>> Mode: {'SIMULATOR' if args.sim else 'REAL'}")
    print(f"  >>> Press Ctrl+C to stop\n")

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        app.run(host=args.host, port=args.web_port, debug=False)
    finally:
        _safe_shutdown()
