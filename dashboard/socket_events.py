import logging
import traceback
from desicion.groundcontrol import GroundControl
from flask_socketio import SocketIO
from desicion.recovery_monitor import RecoveryMonitor
from telemetry.collector import TelemetryCollector
from detection.kalman import KalmanFilter
from detection.cusum import CUSUMDetector
from detection.fault_detector import FaultDetector

log = logging.getLogger(__name__)


def register_socket_events(socketio: SocketIO):

    collector: TelemetryCollector = socketio.telemetry_collector
    kalman_filters: dict[str, KalmanFilter] = socketio.kalman_filters
    cusum_detectors: dict[str, CUSUMDetector] = socketio.cusum_detectors
    fault_detector: FaultDetector = socketio.fault_detector
    groundcontrol: GroundControl = socketio.groundcontrol
    recovery_monitor: RecoveryMonitor = socketio.recovery_monitor
    def stream():
        log.info("Telemetry stream background task started.")

        while True:
            try:
                telemetry = collector.collect()

                filtered = telemetry.copy()

                for key, kf in kalman_filters.items():
                    if key in filtered:
                        filtered[key] = round(kf.filter(float(filtered[key])), 2)

                cusum_results = {}

                for key, detector in cusum_detectors.items():
                    if key in filtered:
                        cusum_results[key] = detector.update(float(filtered[key]))

                faults = fault_detector.detect(filtered)
                recommendation = groundcontrol.generate_recommendation(faults)   
                events = recovery_monitor.update(faults)
                durations = recovery_monitor.active_durations() 


                socketio.emit(
                    "telemetry_update",
                    {
                        "telemetry": filtered,
                        "faults": faults,
                        "cusum": cusum_results,
                        "recommendation": recommendation,
                        "events": events,
                        "durations": durations,
                    },
                )

            except Exception:
                # Without this, an exception here silently kills the
                # background thread and the dashboard hangs on "Connecting"
                # forever with no error shown anywhere in the browser.
                log.error("Telemetry stream loop crashed:\n%s", traceback.format_exc())

            socketio.sleep(1)

            

    socketio.start_background_task(stream)