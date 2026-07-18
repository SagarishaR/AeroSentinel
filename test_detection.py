import time

from flightgear.bridge import FlightGearBridge
from telemetry.collector import TelemetryCollector
from detection.kalman import KalmanFilter
from detection.cusum import CUSUMDetector

bridge = FlightGearBridge()
collector = TelemetryCollector(bridge)

kf = KalmanFilter(
    process_variance=0.01,
    measurement_variance=1.0
)

cusum = CUSUMDetector(
    threshold=5.0,
    drift=0.05
)

try:
    while True:
        telemetry = collector.collect()

        raw_altitude = telemetry["altitude_ft"]
        filtered_altitude = kf.filter(raw_altitude)

        result = cusum.update(filtered_altitude)

        print("-" * 60)
        print(f"Raw Altitude      : {raw_altitude:.2f}")
        print(f"Filtered Altitude : {filtered_altitude:.2f}")
        print(f"CUSUM +           : {result['positive_sum']:.3f}")
        print(f"CUSUM -           : {result['negative_sum']:.3f}")
        print(f"Fault             : {result['fault_detected']}")

        time.sleep(1)

except KeyboardInterrupt:
    bridge.close()