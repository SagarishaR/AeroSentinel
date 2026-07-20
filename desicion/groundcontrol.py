from __future__ import annotations


class GroundControl:
   

    _SEVERITY_RANK = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}

    _RECOMMENDATIONS = {
        "Side-stick Bias": "Manual input trending off-center. Release the stick to neutral and re-check trim before continuing.",
        "Side-stick Stuck": "Side-stick shows no variation across samples — likely jammed. Switch to autopilot or alternate control law and inspect control linkage.",
        "Throttle Bias": "Throttle command elevated above nominal. Reduce power gradually and cross-check N1/N2 for consistency.",
        "Throttle Stuck": "Throttle shows no variation across samples — likely stuck. Disconnect autothrottle, take manual control, prepare for go-around if needed.",
        "Excessive Roll Angle": "Bank angle exceeds the safe limit. Command a wings-level recovery via autopilot and reduce bank immediately.",
        "Engine Anomaly": "N1/N2 readings have diverged beyond tolerance. Cross-check engine instruments; prepare for single-engine procedures if confirmed.",
    }

    def generate_recommendation(self, faults: list[dict], durations: dict | None = None) -> dict:
        if not faults:
            return {"headline": "Nominal ops. No anomalies detected.", "priority": "NONE", "fault": None}

        durations = durations or {}
        primary = max(
            faults,
            key=lambda f: (self._SEVERITY_RANK.get(f["severity"], 0), durations.get(f["fault"], 0))
        )

        return {
            "headline": self._RECOMMENDATIONS.get(
                primary["fault"], f"Unrecognized fault '{primary['fault']}'. Escalate to flight engineer."
            ),
            "priority": primary["severity"],
            "fault": primary["fault"],
        }