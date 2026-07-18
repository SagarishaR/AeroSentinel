from __future__ import annotations

import socket
import threading
from typing import Any


class FlightGearBridge:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5401,
        *,
        timeout: float | None = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._buffer = b""
        self._lock = threading.RLock()

    def connect(self) -> None:
        with self._lock:
            self.disconnect()
            try:
                self._socket = socket.create_connection(
                    (self.host, self.port), timeout=self.timeout
                )
                self._socket.settimeout(self.timeout)
                try:
                    self._read_response()  # Ignore FlightGear welcome banner
                except Exception:
                    pass
            except OSError as error:
                self.disconnect()
                raise ConnectionError(
                    f"Unable to connect to FlightGear at {self.host}:{self.port}"
                ) from error

    def disconnect(self) -> None:
        with self._lock:
            if self._socket is not None:
                try:
                    self._socket.close()
                finally:
                    self._socket = None
                    self._buffer = b""

    def get_property(self, path: str) -> float | int:
        with self._lock:
            self._send_command(f"get {path}")
            return self._parse_property_response(self._read_response())

    def set_property(self, path: str, value: Any) -> None:
        with self._lock:
            self._send_command(f"set {path} {self._format_value(value)}")

        try:
            self._read_response()
        except Exception:
            pass

    def _send_command(self, command: str) -> None:
        if self._socket is None:
            raise ConnectionError("FlightGear bridge is not connected")

        try:
            self._socket.sendall(f"{command}\r\n".encode("utf-8"))
        except OSError as error:
            self.disconnect()
            raise ConnectionError("FlightGear connection was lost") from error

    def _read_response(self) -> str:
        if self._socket is None:
            raise ConnectionError("FlightGear bridge is not connected")

        try:
            while b"\n" not in self._buffer:
                data = self._socket.recv(4096)
                if not data:
                    raise ConnectionError("FlightGear connection was closed")
                self._buffer += data
        except OSError as error:
            self.disconnect()
            raise ConnectionError("FlightGear connection was lost") from error

        response, self._buffer = self._buffer.split(b"\n", 1)
        return response.decode("utf-8").strip()

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _parse_property_response(response: str) -> float | int:
        try:
            value = response.split("=", 1)[1].strip().split(" ", 1)[0]
        except (IndexError, ValueError):
            raise ValueError(f"Invalid FlightGear property response: {response!r}") from None

        value = value.strip("'")
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                raise ValueError(
                    f"FlightGear property value is not numeric: {value!r}"
                ) from None