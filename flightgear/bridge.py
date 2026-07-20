import socket
import time
import logging
import threading

log = logging.getLogger(__name__)


class FlightGearBridge:

    def __init__(self, host="127.0.0.1", port=5401, timeout=0.5, retry_interval=3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.sock = None
        self.connected = False
        self._lock = threading.Lock()
        self._last_attempt = 0.0
        self._connect()

    def _connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            # Read the welcome banner FlightGear sends on connect
            try:
                sock.recv(4096)
            except socket.timeout:
                pass
            self.sock = sock
            self.connected = True
            log.info(f"FlightGear connected at {self.host}:{self.port}")
        except Exception as e:
            log.error(f"FlightGear connection failed: {e}")
            self.connected = False
        finally:
            self._last_attempt = time.time()

    def _ensure_connected(self):
        """Try to (re)connect, but don't hammer FlightGear every single call."""
        if self.connected:
            return True
        if time.time() - self._last_attempt < self.retry_interval:
            return False
        self._connect()
        return self.connected

    def _read_response(self):
        """Read from the socket until a full line arrives or we time out.
        A single recv() call can return a partial line if the response is
        split across TCP packets, which was silently corrupting readings."""
        if self.sock is None:
            return ""

        buffer = b""
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                if b"\n" in buffer:
                    break
            except socket.timeout:
                break
        return buffer.decode("ascii", errors="ignore").strip()

    def get_property(self, prop_path):
        if not self._ensure_connected():
            return 0.0

        with self._lock:
            try:
                cmd = f"get {prop_path}\r\n"
                self.sock.sendall(cmd.encode("ascii"))
                response = self._read_response()

                # Response looks like: /position/altitude-ft = '1250.4' (double)
                for line in response.splitlines():
                    if "=" in line:
                        value_str = line.split("=", 1)[1].strip()
                        if "'" in value_str:
                            value_str = value_str.split("'")[1]
                        return float(value_str)
                return 0.0
            except Exception as e:
                log.warning(f"Get property {prop_path} failed: {e}")
                self.connected = False  # force a reconnect attempt next call
                return 0.0

    def set_property(self, prop_path, value):
        if not self._ensure_connected():
            return False

        with self._lock:
            try:
                cmd = f"set {prop_path} {value:.6f}\r\n"
                self.sock.sendall(cmd.encode("ascii"))
                self._read_response()
                return True
            except Exception as e:
                log.warning(f"Set property {prop_path} failed: {e}")
                self.connected = False
                return False

    def read_state(self):
        return {
            "raw_stick": self.get_property("/controls/flight/elevator"),
            "raw_throttle": self.get_property("/controls/engines/engine[0]/throttle"),

            "altitude_ft": self.get_property("/position/altitude-ft"),
            "airspeed_kts": self.get_property("/velocities/airspeed-kt"),
            "vertical_speed_fpm": self.get_property("/velocities/vertical-speed-fps") * 60,
            "heading_deg": self.get_property("/orientation/heading-deg"),
            "pitch_deg": self.get_property("/orientation/pitch-deg"),
            "roll_deg": self.get_property("/orientation/roll-deg"),

            "engine_n1": self.get_property("/engines/engine[0]/n1"),
            "engine_n2": self.get_property("/engines/engine[0]/n2"),

            "connected": self.connected,
        }

    def write_safe_commands(self, safe_stick, safe_throttle):
        self.set_property("/fdm/jsbsim/fcs/elevator-cmd-norm", safe_stick)
        self.set_property("/fdm/jsbsim/fcs/throttle-cmd-norm[0]", safe_throttle)
        self.set_property("/fdm/jsbsim/fcs/throttle-cmd-norm[1]", safe_throttle)

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        log.info("FlightGear bridge closed")