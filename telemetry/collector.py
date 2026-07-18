from datetime import datetime
from flightgear.bridge import FlightGearBridge


class TelemetryCollector:
    def __init__(self, bridge: FlightGearBridge):
        self.bridge = bridge

    def collect(self):
        data = self.bridge.read_state()
        data["timestamp"] = datetime.now().strftime("%H:%M:%S")
        return data