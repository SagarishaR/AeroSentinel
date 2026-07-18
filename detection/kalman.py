from __future__ import annotations

import numpy as np


class KalmanFilter:
    def __init__(
        self,
        process_variance: float,
        measurement_variance: float,
    ) -> None:
        self.process_variance = float(process_variance)
        self.measurement_variance = float(measurement_variance)

        if self.process_variance < 0 or self.measurement_variance <= 0:
            raise ValueError("Variances must be non-negative, with measurement variance > 0")

        self._estimate: float | None = None
        self._error_covariance = np.float64(1.0)

    def predict(self) -> float | None:
        if self._estimate is None:
            return None

        self._error_covariance += self.process_variance
        return self._estimate

    def update(self, measurement: float) -> float:
        value = float(measurement)

        if self._estimate is None:
            self._estimate = value
            self._error_covariance = np.float64(self.measurement_variance)
            return self._estimate

        gain = self._error_covariance / (
            self._error_covariance + self.measurement_variance
        )
        self._estimate += float(gain * (value - self._estimate))
        self._error_covariance *= 1.0 - gain
        return self._estimate

    def filter(self, measurement: float) -> float:
        self.predict()
        return self.update(measurement)