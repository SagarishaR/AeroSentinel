import time

from flightgear.bridge import FlightGearBridge
from telemetry.collector import TelemetryCollector
from detection.kalman import KalmanFilter
from detection.cusum import CUSUMDetector
from detection.fault_detector import FaultDetector

bridge = FlightGearBridge()
collector = TelemetryCollector(bridge)
detector = FaultDetector()

kalman_filters = {
    "altitude_ft": KalmanFilter(0.01, 1.0),
    "airspeed_kts": KalmanFilter(0.01, 1.0),
    "pitch_deg": KalmanFilter(0.01, 1.0),
    "roll_deg": KalmanFilter(0.01, 1.0),
}

cusum_detectors = {
    "altitude_ft": CUSUMDetector(5.0, 0.05),
    "airspeed_kts": CUSUMDetector(5.0, 0.05),
    "pitch_deg": CUSUMDetector(2.0, 0.02),
    "roll_deg": CUSUMDetector(2.0, 0.02),
}

try:
    while True:

        telemetry = collector.collect()

        filtered = telemetry.copy()

        print("\n" + "=" * 70)

        for sensor, kf in kalman_filters.items():
            filtered[sensor] = kf.filter(telemetry[sensor])

        print("Filtered Sensors")
        print("----------------")

        for sensor in kalman_filters:
            print(f"{sensor:20}: {filtered[sensor]:8.2f}")

        print("\nCUSUM")
        print("-----")

        for sensor, detector_obj in cusum_detectors.items():
            result = detector_obj.update(filtered[sensor])

            print(
                f"{sensor:20}: "
                f"+{result['positive_sum']:.2f} "
                f"-{result['negative_sum']:.2f} "
                f"Fault={result['fault_detected']}"
            )

        faults = detector.detect(filtered)

        print("\nDetected Faults")
        print("----------------")

        if faults:
            for fault in faults:
                print(fault)
        else:
            print("No faults detected.")

        time.sleep(1)

except KeyboardInterrupt:
    bridge.close()