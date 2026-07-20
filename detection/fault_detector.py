from __future__ import annotations


class FaultDetector:
    # Thresholds
    _STICK_BIAS_THRESHOLD = 0.25
    _THROTTLE_BIAS_THRESHOLD = 0.80

    _STUCK_SAMPLE_COUNT = 18
    _STUCK_TOLERANCE = 0.01

    _ROLL_LIMIT_DEG = 45.0

    _ENGINE_DIFFERENCE_LIMIT = 15.0
    _ENGINE_ANOMALY_STREAK_REQUIRED = 5

    _AIRBORNE_SPEED_THRESHOLD_KTS = 20.0

    def __init__(self) -> None:
        self._stick_samples: list[float] = []
        self._throttle_samples: list[float] = []
        self._engine_anomaly_streak = 0

    def detect(self, telemetry: dict) -> list[dict]:
        faults = []

        stick = float(telemetry["raw_stick"])
        throttle = float(telemetry["raw_throttle"])
        roll = float(telemetry["roll_deg"])
        engine_n1 = float(telemetry["engine_n1"])
        engine_n2 = float(telemetry["engine_n2"])
        airspeed = float(telemetry.get("airspeed_kts", 0))

        # Airspeed, not altitude, gates airborne-only checks — altitude MSL
        # is confounded by field elevation (e.g. a parked aircraft can sit
        # at 100+ ft MSL depending on the airport), while airspeed reliably
        # reads ~0 whenever the aircraft is stationary.
        is_airborne = airspeed > self._AIRBORNE_SPEED_THRESHOLD_KTS

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
        # Side-stick / Throttle Stuck
        # ----------------------------
        # Only meaningful once airborne — on the ground, an untouched
        # stick/throttle is expected, not a fault. Requires a longer
        # zero-variance window (18 samples, ~18s) than a simple 5s check,
        # since normal steady-flight moments can easily hold still for a
        # few seconds without indicating a genuine jam.
        if is_airborne:
            if self._is_stuck(self._stick_samples):
                faults.append({
                    "fault": "Side-stick Stuck",
                    "severity": "HIGH",
                    "value": round(stick, 3)
                })

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
        # Requires a sustained streak of over-threshold readings, not a
        # single instantaneous crossing, since a brief N1/N2 spread can be
        # a normal transient (e.g. simulator spawn/reposition) rather than
        # a genuine mechanical divergence.
        engine_difference = abs(engine_n1 - engine_n2)

        if is_airborne and engine_difference > self._ENGINE_DIFFERENCE_LIMIT:
            self._engine_anomaly_streak += 1
        else:
            self._engine_anomaly_streak = 0

        if self._engine_anomaly_streak >= self._ENGINE_ANOMALY_STREAK_REQUIRED:
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