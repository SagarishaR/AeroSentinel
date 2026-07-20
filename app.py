from flask import Flask, render_template
from flask_socketio import SocketIO
from desicion.groundcontrol import GroundControl
from dashboard.socket_events import register_socket_events
from flightgear.bridge import FlightGearBridge
from telemetry.collector import TelemetryCollector
from detection.kalman import KalmanFilter
from detection.cusum import CUSUMDetector
from detection.fault_detector import FaultDetector
from desicion.recovery_monitor import RecoveryMonitor


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    return app, socketio


app, socketio = create_app()


bridge = FlightGearBridge()

collector = TelemetryCollector(bridge)

socketio.telemetry_collector = collector
socketio.groundcontrol = GroundControl()
socketio.recovery_monitor = RecoveryMonitor()
socketio.kalman_filters = {
    "altitude_ft": KalmanFilter(0.01, 1.0),
    "airspeed_kts": KalmanFilter(0.01, 1.0),
    "pitch_deg": KalmanFilter(0.01, 1.0),
    "roll_deg": KalmanFilter(0.01, 1.0),
}

socketio.cusum_detectors = {
    "altitude_ft": CUSUMDetector(5.0, 0.05),
    "airspeed_kts": CUSUMDetector(5.0, 0.05),
    "pitch_deg": CUSUMDetector(2.0, 0.02),
    "roll_deg": CUSUMDetector(2.0, 0.02),
}

socketio.fault_detector = FaultDetector()

register_socket_events(socketio)


if __name__ == "__main__":
    socketio.run(
        app,
        host="127.0.0.1",
        port=5050,
        allow_unsafe_werkzeug=True,
    )

    bridge.close()