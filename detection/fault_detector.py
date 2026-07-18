from __future__ import annotations


class FaultDetector:
    # Thresholds
    _STICK_BIAS_THRESHOLD = 0.25
    _THROTTLE_BIAS_THRESHOLD = 0.80

    _STUCK_SAMPLE_COUNT = 5
    _STUCK_TOLERANCE = 0.01

    _ROLL_LIMIT_DEG = 45.0

    _ENGINE_DIFFERENCE_LIMIT = 15.0

    def __init__(self) -> None:
        self._stick_samples: list[float] = []
        self._throttle_samples: list[float] = []

    def detect(self, telemetry: dict) -> list[dict]:
        faults = []

        stick = float(telemetry["raw_stick"])
        throttle = float(telemetry["raw_throttle"])
        roll = float(telemetry["roll_deg"])
        engine_n1 = float(telemetry["engine_n1"])
        engine_n2 = float(telemetry["engine_n2"])

        # ----------------------------
        # Side-stick Bias
        # ----------------------------
        if abs(stick) > self._STICK_BIAS_THRESHOLD:
            faults.append({
                "fault": "Side-stick Bias",
                "severity": "MEDIUM",
                "value": round(stick, 3)
            })

        # ----------------------------
        # Throttle Bias
        # ----------------------------
        if throttle > self._THROTTLE_BIAS_THRESHOLD:
            faults.append({
                "fault": "Throttle Bias",
                "severity": "MEDIUM",
                "value": round(throttle, 3)
            })

        # ----------------------------
        # Store history
        # ----------------------------
        self._record_sample(self._stick_samples, stick)
        self._record_sample(self._throttle_samples, throttle)

        # ----------------------------
        # Side-stick Stuck
        # ----------------------------
        if self._is_stuck(self._stick_samples):
            faults.append({
                "fault": "Side-stick Stuck",
                "severity": "HIGH",
                "value": round(stick, 3)
            })

        # ----------------------------
        # Throttle Stuck
        # ----------------------------
        if self._is_stuck(self._throttle_samples):
            faults.append({
                "fault": "Throttle Stuck",
                "severity": "HIGH",
                "value": round(throttle, 3)
            })

        # ----------------------------
        # Excessive Roll
        # ----------------------------
        if abs(roll) > self._ROLL_LIMIT_DEG:
            faults.append({
                "fault": "Excessive Roll Angle",
                "severity": "HIGH",
                "value": round(roll, 2)
            })

        # ----------------------------
        # Engine Anomaly
        # ----------------------------
        engine_difference = abs(engine_n1 - engine_n2)

        if engine_difference > self._ENGINE_DIFFERENCE_LIMIT:
            faults.append({
                "fault": "Engine Anomaly",
                "severity": "HIGH",
                "value": round(engine_difference, 2)
            })

        return faults

    def _record_sample(self, samples: list[float], value: float) -> None:
        samples.append(value)

        if len(samples) > self._STUCK_SAMPLE_COUNT:
            samples.pop(0)

    def _is_stuck(self, samples: list[float]) -> bool:
        if len(samples) < self._STUCK_SAMPLE_COUNT:
            return False

        return (max(samples) - min(samples)) <= self._STUCK_TOLERANCE