const socket = io();

const el = (id) => document.getElementById(id);

let missionStartTime = null;
let timerInterval = null;
let firstDataReceived = false;

function startMissionTimer() {
  if (timerInterval) return;
  missionStartTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsedMs = Date.now() - missionStartTime;
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const hh = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
    const mm = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
    const ss = String(totalSeconds % 60).padStart(2, "0");
    el("mission-timer").textContent = `${hh}:${mm}:${ss}`;
  }, 1000);
}

function setConnectionUI(isConnected) {
  const pulse = el("conn-pulse");
  const text = el("conn-text");
  const commState = el("comm-state");
  const feedTag = el("feed-tag");

  if (isConnected) {
    pulse.style.background = "var(--success)";
    text.textContent = "Flight Status: Live";
    commState.textContent = "Online";
    feedTag.textContent = "LIVE FEED";
  } else {
    pulse.style.background = "#ff5f6d";
    text.textContent = "Simulator Disconnected";
    commState.textContent = "Offline";
    feedTag.textContent = "NO SIGNAL";
  }
}

function renderTelemetry(telemetry) {
  el("metric-altitude").textContent = `${Math.round(telemetry.altitude_ft ?? 0)}`;
  el("metric-altitude-unit").textContent = "ft MSL";

  el("metric-airspeed").textContent = `${Math.round(telemetry.airspeed_kts ?? 0)}`;
  el("metric-airspeed-unit").textContent = "kts";

  el("metric-pitch").textContent = `${(telemetry.pitch_deg ?? 0).toFixed(1)}°`;
  el("metric-pitch-unit").textContent = "pitch";

  el("metric-roll").textContent = `${(telemetry.roll_deg ?? 0).toFixed(1)}°`;
  el("metric-roll-unit").textContent = "roll";

  el("telemetry-raw-1").innerHTML =
    `<span class="pulse" style="width:6px;height:6px;display:inline-block;margin-right:6px;"></span>Heading ${Math.round(telemetry.heading_deg ?? 0)}°  |  V/S ${Math.round(telemetry.vertical_speed_fpm ?? 0)} fpm`;
  el("telemetry-raw-2").innerHTML =
    `<span class="pulse" style="width:6px;height:6px;display:inline-block;margin-right:6px;"></span>N1 ${(telemetry.engine_n1 ?? 0).toFixed(1)}%  |  N2 ${(telemetry.engine_n2 ?? 0).toFixed(1)}%`;

  const altitude = telemetry.altitude_ft ?? 0;
  el("flight-phase").textContent = altitude > 50 ? "Airborne" : "On Ground";
  el("silhouette-label").textContent = `ALT ${Math.round(altitude)} ft  ·  HDG ${Math.round(telemetry.heading_deg ?? 0)}°`;
}
function renderRecommendation(rec) {
  const text = el("ai-recommendation");
  if (!rec || rec.priority === "NONE") {
    text.textContent = "Nominal ops. No anomalies detected.";
    text.style.color = "var(--muted)";
    return;
  }
  text.textContent = rec.headline;
  text.style.color = rec.priority === "HIGH" ? "#ff8a8a" : "#ffcf7a";
}
function renderFaults(faults, durations) {
  const countBadge = el("faults-count");
  const emptyState = el("faults-empty");
  const listContainer = el("faults-list");
  const health = el("system-health");

  countBadge.textContent = faults.length;

  if (!faults.length) {
    emptyState.style.display = "grid";
    listContainer.style.display = "none";
    listContainer.innerHTML = "";
    health.textContent = "Nominal";
    health.style.color = "var(--success)";
    return;
  }

  emptyState.style.display = "none";
  listContainer.style.display = "block";

  const highFaults = faults.filter((f) => f.severity === "HIGH");
  const sustainedHigh = highFaults.some((f) => (durations?.[f.fault] ?? 0) >= 10);

  if (sustainedHigh) {
    health.textContent = "Critical";
    health.style.color = "#ff8a8a";
  } else if (highFaults.length) {
    health.textContent = "Warning";
    health.style.color = "#ffcf7a";
  } else {
    health.textContent = "Degraded";
    health.style.color = "#ffcf7a";
  }

  listContainer.innerHTML = faults
    .map((f) => {
      const duration = durations?.[f.fault];
      const durationLabel = duration !== undefined ? ` · active ${duration}s` : "";
      return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);">
        <span style="font-size:12px;color:var(--text);">${f.fault}</span>
        <span style="font-family:var(--mono);font-size:10px;color:${f.severity === "HIGH" ? "#ff8a8a" : "#ffcf7a"};">
          ${f.severity} · ${f.value}${durationLabel}
        </span>
      </div>`;
    })
    .join("");
}
function describeEvent(event) {
  const time = new Date().toLocaleTimeString();
  switch (event.event) {
    case "STARTED": return `[${time}] ${event.fault} detected (${event.severity}).`;
    case "RECOVERING": return `[${time}] ${event.fault} trending toward resolution.`;
    case "ESCALATING": return `[${time}] ${event.fault} worsening — reassess.`;
    case "RESOLVED": return `[${time}] ${event.fault} resolved after ${event.duration_seconds}s.`;
    default: return `[${time}] ${event.fault}: ${event.event}`;
  }
}

function logTimelineEvent(event) {
  const container = el("timeline-container");

  if (container.querySelector("p")?.textContent === "Timeline events will appear here.") {
    container.innerHTML = "";
    // Switch from the placeholder's horizontal layout to a vertical,
    // scrollable list once real events start coming in.
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "10px";
    container.style.maxHeight = "220px";
    container.style.overflowY = "auto";
    container.style.alignItems = "stretch";
  }

  const entry = document.createElement("div");
  entry.style.cssText = "display:flex;gap:10px;align-items:flex-start;";
  entry.innerHTML = `<span style="width:1px;align-self:stretch;background:linear-gradient(var(--accent),transparent);flex-shrink:0;"></span><p style="margin:0;font-size:11px;color:var(--text);">${describeEvent(event)}</p>`;
  container.appendChild(entry);

  container.scrollTop = container.scrollHeight;
}
function logCommEvent(message, skipTimestamp = false) {
  const log = el("comm-log");
  if (log.querySelector("p")?.textContent === "Communication log is empty.") {
    log.innerHTML = "";
  }
  const line = document.createElement("p");
  line.textContent = skipTimestamp ? message : `[${new Date().toLocaleTimeString()}] ${message}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

socket.on("connect", () => {
  console.log("Connected to dashboard server");
});

socket.on("disconnect", () => {
  setConnectionUI(false);
  logCommEvent("Lost connection to dashboard server.");
});

socket.on("telemetry_update", (data) => {
  const telemetry = data.telemetry || {};
  const faults = data.faults || [];

  // telemetry.connected reflects whether the Python backend is actually
  // talking to FlightGear (as opposed to the browser-to-server socket).
  setConnectionUI(telemetry.connected !== false);

  if (!firstDataReceived) {
    firstDataReceived = true;
    startMissionTimer();
    logCommEvent("Telemetry stream established.");
  }

  renderTelemetry(telemetry);
  renderFaults(faults, data.durations);
  renderRecommendation(data.recommendation);
  (data.events || []).forEach((event) => {   // ← this block is missing
    logTimelineEvent(event);
    logCommEvent(describeEvent(event),true);
  });
  
});