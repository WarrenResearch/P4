import re
import time

import serial


class Balance(object):
    """Serial driver for a Kern PFB balance.

    The balance command set can vary slightly between models and firmware
    revisions, so the command strings are configurable. The driver focuses on
    the common operations needed for automation: connect, read weight, tare,
    zero, and send arbitrary commands.
    """

    def __init__(
        self,
        port=None,
        baudrate=9600,
        timeout=1,
        write_termination="\r",
        read_termination="\r\n",
        encoding="ascii",
        read_command="SI",
        tare_command="T",
        zero_command="Z",
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_termination = write_termination
        self.read_termination = read_termination
        self.encoding = encoding
        self.read_command = read_command
        self.tare_command = tare_command
        self.zero_command = zero_command
        self.serial = None
        self.last_response = ""

        if self.port is not None:
            self.connect(self.port)

    def connect(self, port=None):
        if port is not None:
            self.port = port

        if self.port is None:
            raise ValueError("A serial port must be provided before connecting.")

        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        print("Kern PFB balance connected on port " + str(self.port))
        return self

    def close(self):
        if self.serial is not None and self.serial.is_open:
            self.serial.close()

    def is_connected(self):
        return self.serial is not None and self.serial.is_open

    def _ensure_connection(self):
        if not self.is_connected():
            raise RuntimeError("Balance is not connected. Call connect() first.")

    def _write(self, command):
        self._ensure_connection()
        payload = (str(command) + self.write_termination).encode(self.encoding)
        self.serial.write(payload)

    def _read_line(self):
        self._ensure_connection()
        response = self.serial.readline()
        if not response:
            return ""
        return response.decode(self.encoding, errors="ignore").strip("\r\n\x00 ")

    def query(self, command, wait=0.1):
        self._write(command)
        if wait:
            time.sleep(wait)
        self.last_response = self._read_line()
        return self.last_response

    @staticmethod
    def parse_weight(response):
        """Extract the first numeric weight value from a balance response."""
        if response is None:
            return None

        match = re.search(r"[-+]?\d+(?:[\.,]\d+)?", str(response))
        if not match:
            return None

        return float(match.group(0).replace(",", "."))

    def read_weight(self, command=None, stable_only=False, wait=0.1):
        """Query the balance and return the parsed weight.

        If the exact balance command differs from the default, pass an explicit
        command string.
        """
        if command is None:
            command = self.read_command

        response = self.query(command, wait=wait)
        if stable_only and response and not self._looks_stable(response):
            return None

        return self.parse_weight(response)

    def read_raw(self, command=None, wait=0.1):
        if command is None:
            command = self.read_command
        return self.query(command, wait=wait)

    def tare(self, command=None, wait=0.2):
        if command is None:
            command = self.tare_command
        return self.query(command, wait=wait)

    def zero(self, command=None, wait=0.2):
        if command is None:
            command = self.zero_command
        return self.query(command, wait=wait)

    def send(self, command, wait=0.1):
        """Send a custom command and return the raw response."""
        return self.query(command, wait=wait)

    @staticmethod
    def _looks_stable(response):
        upper_response = str(response).upper()
        return any(token in upper_response for token in ("ST", "S ", "STABLE"))