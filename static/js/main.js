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

const SPARKLINE_LENGTH = 30;
const sparklineData = { vspeed: [], n1: [], n2: [] };

function pushSparklinePoint(key, value) {
  const arr = sparklineData[key];
  arr.push(value);
  if (arr.length > SPARKLINE_LENGTH) arr.shift();
}

function buildSparklinePath(values, width = 300, height = 80, padding = 6) {
  if (values.length < 2) return { line: "", fill: "" };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = (width - padding * 2) / (values.length - 1);

  const points = values.map((v, i) => {
    const x = padding + i * stepX;
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return [x, y];
  });

  const line = points.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(" ");
  const fill = `${line} L${points[points.length - 1][0]},${height} L${points[0][0]},${height} Z`;
  return { line, fill };
}

function renderSparkline(lineId, values, fillId = null) {
  const { line, fill } = buildSparklinePath(values);
  const lineEl = document.getElementById(lineId);
  if (lineEl) lineEl.setAttribute("d", line);
  if (fillId) {
    const fillEl = document.getElementById(fillId);
    if (fillEl) fillEl.setAttribute("d", fill);
  }
}

function updateHealthGauge(statusText) {
  const ring = el("health-ring");
  if (!ring) return;
  const circumference = 87.96;
  let fraction = 1;
  let color = "var(--success)";
  let pulse = false;

  if (statusText === "Warning") {
    fraction = 0.66;
    color = "#ffcf7a";
  } else if (statusText === "Critical") {
    fraction = 1;
    color = "#ff8a8a";
    pulse = true;
  } else {
    fraction = 1;
    color = "var(--success)";
  }

  ring.style.stroke = color;
  ring.style.strokeDashoffset = circumference * (1 - fraction);
  ring.classList.toggle("pulse-ring", pulse);
}

const metricAnimState = {};

function animateMetric(elId, newValue, decimals = 0, suffix = "") {
  const target = document.getElementById(elId);
  if (!target) return;
  const start = metricAnimState[elId] ?? newValue;
  metricAnimState[elId] = newValue;

  const end = newValue;
  const duration = 400;
  const startTime = performance.now();

  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (end - start) * eased;
    target.textContent = `${current.toFixed(decimals)}${suffix}`;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function renderTelemetry(telemetry) {
  animateMetric("metric-altitude", Math.round(telemetry.altitude_ft ?? 0), 0);
  el("metric-altitude-unit").textContent = "ft MSL";

  animateMetric("metric-airspeed", Math.round(telemetry.airspeed_kts ?? 0), 0);
  el("metric-airspeed-unit").textContent = "kts";

  animateMetric("metric-pitch", telemetry.pitch_deg ?? 0, 1, "°");
  el("metric-pitch-unit").textContent = "pitch";

  animateMetric("metric-roll", telemetry.roll_deg ?? 0, 1, "°");
  el("metric-roll-unit").textContent = "roll";

  pushSparklinePoint("vspeed", telemetry.vertical_speed_fpm ?? 0);
  pushSparklinePoint("n1", telemetry.engine_n1 ?? 0);
  pushSparklinePoint("n2", telemetry.engine_n2 ?? 0);
  renderSparkline("vspeedLine", sparklineData.vspeed, "vspeedFill");
  renderSparkline("n1Line", sparklineData.n1, "n1Fill");
  renderSparkline("n2Line", sparklineData.n2);

  el("telemetry-raw-1").innerHTML =
    `<span class="pulse" style="width:6px;height:6px;display:inline-block;margin-right:6px;"></span>V/S ${Math.round(telemetry.vertical_speed_fpm ?? 0)} fpm`;
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

let previousFaultSeverity = {};

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
    updateHealthGauge("Nominal");
    previousFaultSeverity = {};
    return;
  }

  emptyState.style.display = "none";
  listContainer.style.display = "block";

  const highFaults = faults.filter((f) => f.severity === "HIGH");
  const sustainedHigh = highFaults.some((f) => (durations?.[f.fault] ?? 0) >= 10);
  let statusText;

  if (sustainedHigh) {
    statusText = "Critical";
    health.style.color = "#ff8a8a";
  } else if (highFaults.length) {
    statusText = "Warning";
    health.style.color = "#ffcf7a";
  } else {
    statusText = "Degraded";
    health.style.color = "#ffcf7a";
  }
  health.textContent = statusText;
  updateHealthGauge(statusText === "Degraded" ? "Warning" : statusText);

  const currentSeverity = {};
  listContainer.innerHTML = faults
    .map((f) => {
      currentSeverity[f.fault] = f.severity;
      const changed = previousFaultSeverity[f.fault] !== f.severity;
      const duration = durations?.[f.fault];
      const durationLabel = duration !== undefined ? ` · active ${duration}s` : "";
      return `
      <div class="fault-row ${changed ? "fault-row-flash" : ""}">
        <span style="font-size:12px;color:var(--text);">${f.fault}</span>
        <span style="font-family:var(--mono);font-size:10px;color:${f.severity === "HIGH" ? "#ff8a8a" : "#ffcf7a"};">
          ${f.severity} · ${f.value}${durationLabel}
        </span>
      </div>`;
    })
    .join("");
  previousFaultSeverity = currentSeverity;
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


  setConnectionUI(telemetry.connected !== false);

  if (!firstDataReceived) {
    firstDataReceived = true;
    startMissionTimer();
    logCommEvent("Telemetry stream established.");
  }

  renderTelemetry(telemetry);
  renderFaults(faults, data.durations);
  renderRecommendation(data.recommendation);

  (data.events || []).forEach((event) => {
    logTimelineEvent(event);
    logCommEvent(describeEvent(event), true);
  });
});

socket.on("question_answer", (result) => {
  logCommEvent(`[Ground Query] ${result.answer}`, true);
});
