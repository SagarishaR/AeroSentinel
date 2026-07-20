<div align="center">

# ✈️ AeroSentinel — Ground Control Decision Support System

Built for OpenAI Build Week**
<br/>
![OpenAI Codex](https://img.shields.io/badge/Built%20with-OpenAI%20Codex-6F42C1?style=for-the-badge&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![Socket.IO](https://img.shields.io/badge/Socket.IO-010101?style=for-the-badge\&logo=socketdotio\&logoColor=white)
![FlightGear](https://img.shields.io/badge/FlightGear-Simulator-blue?style=for-the-badge)
![Kalman Filter](https://img.shields.io/badge/Kalman_Filter-Anomaly_Detection-green?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge\&logo=flask\&logoColor=white)
![CUSUM](https://img.shields.io/badge/CUSUM-Drift_Detection-orange?style=for-the-badge)


</div>

AeroSentinel is a real-time ground control dashboard that watches a simulated aircraft's flight data, automatically detects specific in-flight problems, and displays the correct emergency recovery guidance — the same way a real ground control team would radio instructions to a pilot.

It connects to a live [FlightGear](https://www.flightgear.org/) flight simulation, filters and analyzes the telemetry stream in real time, and turns raw sensor noise into clear, actionable, timestamped guidance on a live dashboard.

---

## 🎯 The Idea, in One Sentence

> When something goes wrong on the aircraft, ground control detects it, decides what to do, and gets that guidance to the pilot — instantly and completely offline, because in flight, there is no internet connection to rely on.

---

## Why This Project Exists

In a real cockpit emergency, a pilot doesn't have time to interpret raw instrument noise. Ground control (or onboard alerting systems) need to:

1. **Notice** something is wrong, fast and reliably — not on every noisy blip.
2. **Know what it means** — translate a raw number into a named, categorized problem.
3. **Say what to do about it** — clearly, consistently, every time.
4. **Track whether it's working** — is the situation improving, or getting worse?

AeroSentinel builds a working, end-to-end version of that loop using real telemetry from a flight simulator — not a mockup, not canned data.

---

## 🤖 How GPT-5.6 and Codex Were Actually Used

Per Build Week's guidance, here's an honest, specific account .

GPT-5.6, accessed through Codex, was used **only during development**, never at runtime. Specifically:

| Area | How Codex/GPT-5.6 helped | What we decided ourselves |
|---|---|---|
| **Debugging** | Diagnosed a chain of real bugs: a frontend that never rendered to the DOM, a hanging CDN dependency for socket.io, a Flask 404 from a misplaced static file, and a background thread crashing silently on an unhandled exception. | Verified each fix against our own running system and FlightGear session before accepting it. |
| **Fault-detection logic** | Helped identify and fix two real false-positive bugs: using MSL altitude (confounded by airport elevation) instead of airspeed to detect "airborne," and a too-short "stuck control" window that flagged completely normal steady-flight behavior as a fault. | Chose the actual thresholds (18-sample stuck window, airspeed-only airborne gate, 5-sample engine-anomaly streak) based on testing against real simulator behavior — these are our judgment calls, not generated defaults. |
| **Recovery recommendation wording** | Reviewed and helped phrase the six recovery instructions in aviation-appropriate, stress-tested language. | Wrote and owned the fault → recommendation mapping itself, and decided this had to be a fixed rulebook, not a live model call — a safety-critical design decision made independently of any AI suggestion. |
| **Frontend scaffolding** | Helped generate boilerplate UI code (chart rendering, animation wiring, layout structure). | Made all layout, color palette, and information-hierarchy decisions.|
| **Recovery-monitoring state machine** | Helped scaffold the STARTED → RECOVERING → ESCALATING → RESOLVED state-tracking logic. | Defined the actual trend thresholds (improvement/worsening ratios) based on what made sense for this system. |

**In short:** Codex accelerated implementation and helped catch real bugs faster than manual debugging would have — but every threshold, every design decision about *when* something counts as a fault, and the decision to keep the recommendation engine fully rule-based  were made and owned by us.

---

## 🚨 Faults Detected

AeroSentinel monitors for **six** aircraft fault conditions, each mapped to a specific, ground-control-style recovery instruction:

| # | Fault | What triggers it | Severity |
|---|---|---|---|
| 1 | **Side-stick Bias** | Manual control input deflected beyond a safe threshold, but still actively varying | MEDIUM |
| 2 | **Side-stick Stuck** | Control input frozen (near-zero variance) for a sustained period while the aircraft is airborne | HIGH |
| 3 | **Throttle Bias** | Throttle command sustained above a safe power threshold | MEDIUM |
| 4 | **Throttle Stuck** | Throttle frozen (near-zero variance) for a sustained period while airborne | HIGH |
| 5 | **Excessive Roll Angle** | Bank angle exceeds a safe limit (±45°) | HIGH |
| 6 | **Engine Anomaly** | Sustained divergence between engine N1/N2 spool speeds beyond tolerance | HIGH |

Each fault, when detected, produces:
- An entry in the **Active Faults** panel, with live-updating duration
- A matching entry in the **AI Ground Control** recommendation panel (highest-severity, longest-active fault takes priority when multiple are active)
- A timestamped **STARTED** event in the Mission Timeline and Communication Log
- Follow-up **RECOVERING**, **ESCALATING**, or **RESOLVED** events as the situation develops, each with elapsed duration

### A note on detection design (real-world honesty)

Two specific engineering decisions were made after finding real false positives during testing, and are worth knowing:

- **"Stuck" detection requires ~18 seconds of zero-variance input**, not just a few seconds — because a pilot naturally holds controls nearly still during normal, calm, level flight, and a shorter window falsely flagged that as a jam.
- **Airborne-only checks are gated on airspeed, not altitude** — because altitude above sea level is affected by airport elevation, and using it caused false "in-flight" faults while the aircraft was still parked on the ground at a field with nonzero elevation.

These are documented, deliberate tradeoffs, not oversights — a production system would likely add further corroborating signals (e.g., commanded vs. actual control-surface position, autopilot engagement state) to further reduce false positives.

---

## 🏗️ System Architecture

```
FlightGear (simulated aircraft, telnet property server)
        │
        ▼
FlightGearBridge          — TCP/telnet client, auto-reconnects every 3s
        │
        ▼
TelemetryCollector         — pulls raw altitude, airspeed, pitch, roll,
        │                     heading, engine N1/N2, stick, throttle
        ▼
KalmanFilter (per channel) — smooths noisy sensor readings
        │
        ▼
CUSUMDetector (per channel)— flags gradual sensor drift
        │
        ▼
FaultDetector               — classifies into 6 known fault types
        │
        ├──▶ GroundControl        — rule-based recovery recommendation
        │
        └──▶ RecoveryMonitor      — tracks fault trend over time
                                     (STARTED/RECOVERING/ESCALATING/RESOLVED)
        │
        ▼
Flask-SocketIO backend      — emits telemetry_update every ~1s
        │
        ▼
Live browser dashboard      — telemetry, faults, recommendations,
                               mission timeline, communication log
```

---

## 🛠️ Tech Stack

- **Python 3.x**, **Flask**, **Flask-SocketIO** (threading async mode)
- **NumPy** — Kalman filter math
- **FlightGear** — flight simulator, connected via its raw TCP/telnet property interface
- **Vanilla JavaScript + Socket.IO client** (bundled locally, not loaded from a CDN — this avoids a real bug we hit where an external CDN request silently hung and blocked the entire dashboard from initializing)
- No frontend framework, no build step — plain HTML/CSS/JS served directly by Flask

---

## 📋 Prerequisites

Before you begin, make sure you have:

1. **Python 3.10+** installed
   ```bash
   python3 --version
   ```
2. **FlightGear** (free, open-source flight simulator) — [download here](https://www.flightgear.org/download/)
   - Any recent version (2020.3+) works fine
   - You will also need at least one aircraft installed via FlightGear's built-in aircraft downloader (e.g. the default Cessna 172P, or a larger airliner like the 787-8 if available)
3. **pip** for installing Python dependencies
4. A machine that can run FlightGear smoothly — it's graphically intensive; a dedicated GPU is recommended but not strictly required

---

## ✈️ Step 1 — Set Up and Launch FlightGear

FlightGear needs to expose a **telnet property server** so AeroSentinel can read live telemetry from it.

### Launching with telnet enabled

**Option A — via the FlightGear Launcher (GUI)**
1. Open FlightGear.
2. Go to the **Settings** tab.
3. Under **Additional Settings**, add the following command-line option:
   ```
   --telnet=5401
   ```
4. Choose your aircraft and airport as normal, then click **Fly!**

**Option B — via command line**
```bash
fgfs --telnet=5401 --aircraft=787-8 --airport=KSFO
```
(Substitute your preferred aircraft and airport codes.)

### Verifying the telnet server is running

Once FlightGear has finished loading, confirm the telnet interface is live:
```bash
telnet 127.0.0.1 5401
```
- If you get a connected prompt (something like a `/` root path readout) — you're good, disconnect and move on.
- If it hangs or refuses the connection — FlightGear either hasn't finished loading yet, or wasn't launched with the `--telnet=5401` flag. Double-check and retry.

### Recommended: start in the air (for faster testing)

Rather than taxiing and taking off manually every time, use FlightGear's **Position** dialog (Location menu → Reset, or similar depending on your version) to spawn already airborne:
- **Position mode:** "In Air"
- **Altitude:** `8000` ft
- **Airspeed:** `220` kt

This drops you into stable, level flight — enough airspeed to clear AeroSentinel's airborne-detection threshold, and a safe speed/altitude margin for testing roll and control-input faults without risking a structural overstress event in the simulator.

---

## 💻 Step 2 — Clone and Set Up AeroSentinel

```bash
# 1. Clone the repository
git clone <YOUR_REPO_URL_HERE>
cd AeroSentinel

# 2. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

If you don't have a `requirements.txt` yet, at minimum you'll need:
```bash
pip install flask flask-socketio numpy
```

---

## ▶️ Step 3 — Run the Dashboard

With **FlightGear already running** (telnet server confirmed live, per Step 1):

```bash
python app.py
```

You should see:
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5050
Telemetry stream background task started.
```

Now open your browser to:
```
http://127.0.0.1:5050
```

The dashboard should connect automatically and begin showing live telemetry within a second or two. If the badge is stuck on "Connecting," see the **Troubleshooting** section below.

---

## 🧪 Step 4 — Trigger and Observe a Fault (Quick Test)

Once the dashboard is live and showing telemetry:

1. **Roll test (fastest, safest):** Hold the right or left arrow key briefly to bank the aircraft past 45°, then release and correct back to level.
   - Watch the **Active Faults** card — `Excessive Roll Angle` should appear within a second, HIGH severity.
   - Watch the **AI Ground Control** panel — it should display the matching recovery instruction.
   - Watch the **Mission Timeline** — a `STARTED` event should log, followed by `RESOLVED` once you level out.

2. **Stuck-control test:** Let go of all controls entirely and don't touch anything for about 20 seconds.
   - `Side-stick Stuck` and/or `Throttle Stuck` should appear, since the detector treats a truly frozen control as a possible jam.
   - Touch the stick or throttle again — the fault should clear on its own.

If both of these work, your setup is confirmed end-to-end.

---

## 🩺 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Dashboard stuck on "Connecting" | Browser never opened a socket connection | Check DevTools → Network tab for a stalled `socket.io.min.js` request; hard-refresh with cache disabled |
| Badge says "Simulator Disconnected" | FlightGear's telnet server isn't reachable | Confirm FlightGear was launched with `--telnet=5401` and has finished loading; check with `telnet 127.0.0.1 5401` |
| All faults read 0 / no data changes | FlightGear connection dropped after start | The bridge retries every 3 seconds automatically — give it a few seconds, or restart Flask after confirming FlightGear is up |
| `404` on `socket.io.min.js` | File missing from `static/js/` | Confirm the file exists at exactly `static/js/socket.io.min.js` |
| False HIGH faults while parked on the ground | Old build without the airspeed-gating fix | Confirm `detection/fault_detector.py` gates airborne checks on airspeed, not altitude |
| Terminal shows a traceback from the background thread | An unhandled exception in the telemetry loop | Read the logged traceback — logging is enabled specifically so this is never a silent failure |

---

## 📁 Project Structure

```
AeroSentinel/
├── app.py                          # Flask app entry point, wires up all services
├── requirements.txt
├── flightgear/
│   └── bridge.py                   # Telnet client, auto-reconnect, property parsing
├── telemetry/
│   └── collector.py                # Pulls and structures raw telemetry
├── detection/
│   ├── kalman.py                   # Per-channel Kalman filter
│   ├── cusum.py                    # CUSUM drift detector
│   └── fault_detector.py           # Classifies the 6 fault types
├── desicion/                       # Decision-support layer
│   ├── groundcontrol.py            # Rule-based recovery recommendation engine
│   └── recovery_monitor.py         # Fault trend tracking / state machine
├── dashboard/
│   └── socket_events.py            # Background telemetry loop, Socket.IO emit
├── templates/
│   └── index.html                  # Dashboard UI
└── static/
    ├── css/style.css
    └── js/
        ├── main.js                 # Dashboard rendering + socket handling
        └── socket.io.min.js        # Bundled locally (not loaded from a CDN)
```

---

## 🔮 Future Work

- Optional live-LLM-assisted analysis on the **ground-station side only** (where network connectivity exists), while keeping the in-flight/offline path fully rule-based for safety and availability.
- Cross-checking commanded vs. actual control-surface position to sharpen stuck-control detection.
- Multi-fault recommendation display instead of single highest-priority fault.
- Expanded fault taxonomy (electrical, hydraulic, pressurization).

---

## 📄 License

This project is licensed under the MIT License.

---

*Built for OpenAI Build Week. GPT-5.6, via Codex, assisted development.*
