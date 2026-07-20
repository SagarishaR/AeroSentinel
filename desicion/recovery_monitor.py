from __future__ import annotations
import time


class RecoveryMonitor:
   

    _TREND_WINDOW = 5          # how many recent values we compare
    _IMPROVEMENT_RATIO = 0.85  # value must shrink to 85% of its starting point to count as recovering
    _WORSEN_RATIO = 1.15       # value must grow to 115% of its starting point to count as escalating

    def __init__(self) -> None:
        self._active: dict[str, dict] = {}

    def update(self, faults: list[dict]) -> list[dict]:
        """Call once per telemetry tick with the current fault list.
        Returns state-change events (STARTED / RECOVERING / ESCALATING /
        RESOLVED) that happened this tick, for logging on the dashboard."""
        now = time.time()
        events = []
        seen_this_tick = set()

        for fault in faults:
            name = fault["fault"]
            value = abs(fault["value"])
            seen_this_tick.add(name)

            if name not in self._active:
                self._active[name] = {
                    "first_seen": now,
                    "initial_value": value,
                    "history": [value],
                    "status": "ACTIVE",
                }
                events.append({"fault": name, "event": "STARTED", "severity": fault["severity"]})
                continue

            record = self._active[name]
            record["history"].append(value)
            record["history"] = record["history"][-self._TREND_WINDOW:]

            recent_avg = sum(record["history"]) / len(record["history"])
            baseline = record["initial_value"] or 1e-6  # guard divide-by-zero

            previous_status = record["status"]
            if recent_avg <= baseline * self._IMPROVEMENT_RATIO:
                record["status"] = "RECOVERING"
            elif recent_avg >= baseline * self._WORSEN_RATIO:
                record["status"] = "ESCALATING"
            else:
                record["status"] = "ACTIVE"

            if record["status"] != previous_status:
                events.append({"fault": name, "event": record["status"], "severity": fault["severity"]})

        # tracked faults that vanished from this tick's list have resolved
        for name in list(self._active.keys()):
            if name not in seen_this_tick:
                duration = round(now - self._active[name]["first_seen"], 1)
                events.append({"fault": name, "event": "RESOLVED", "duration_seconds": duration})
                del self._active[name]

        return events

    def active_durations(self) -> dict[str, float]:
        """Seconds each currently-active fault has been ongoing."""
        now = time.time()
        return {name: round(now - rec["first_seen"], 1) for name, rec in self._active.items()}