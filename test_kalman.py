import time

from detection.kalman import KalmanFilter
from flightgear.bridge import FlightGearBridge
from telemetry.collector import TelemetryCollector

bridge = FlightGearBridge()
collector = TelemetryCollector(bridge)

filters = {
    "altitude_ft": KalmanFilter(0.01, 1.0),
    "airspeed_kts": KalmanFilter(0.01, 1.0),
    "pitch_deg": KalmanFilter(0.01, 1.0),
    "roll_deg": KalmanFilter(0.01, 1.0),
}

try:
    while True:
        telemetry = collector.collect()

        print("\n---------------------------")

        for sensor, kf in filters.items():
            raw = telemetry[sensor]
            filtered = kf.filter(raw)
            print(f"{sensor:15} Raw: {raw:8.2f}  Filtered: {filtered:8.2f}")

        time.sleep(1)

except KeyboardInterrupt:
    bridge.close()