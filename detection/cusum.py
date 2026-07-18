from __future__ import annotations


class CUSUMDetector:
    def __init__(self, threshold: float, drift: float) -> None:
        self.threshold = float(threshold)
        self.drift = float(drift)

        if self.threshold <= 0 or self.drift < 0:
            raise ValueError("Threshold must be positive and drift must be non-negative")

        self.reset()

    def update(self, value: float) -> dict[str, float | bool]:
        observation = float(value)

        if self.reference_value is None:
            self.reference_value = observation
        else:
            deviation = observation - self.reference_value
            self.positive_sum = max(
                0.0, self.positive_sum + deviation - self.drift
            )
            self.negative_sum = max(
                0.0, self.negative_sum - deviation - self.drift
            )

        return {
            "positive_sum": self.positive_sum,
            "negative_sum": self.negative_sum,
            "fault_detected": (
                self.positive_sum > self.threshold
                or self.negative_sum > self.threshold
            ),
        }

    def reset(self) -> None:
        self.reference_value: float | None = None
        self.positive_sum = 0.0
        self.negative_sum = 0.0