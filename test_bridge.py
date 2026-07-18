from flightgear.bridge import FlightGearBridge
from telemetry.collector import TelemetryCollector
import time

bridge = FlightGearBridge()
collector = TelemetryCollector(bridge)

collector = TelemetryCollector(bridge)

try:
    while True:
        telemetry = collector.collect()
        print(telemetry)
        time.sleep(1)

except KeyboardInterrupt:
    bridge.close()