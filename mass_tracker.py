"""
Standalone real-time mass tracker for A&D HR-A / HR-AZ series analytical
balances (HR-250AZ, HR-150AZ, HR-100AZ, HR-250A, HR-150A, HR-100A).

Polls the balance over its RS-232C serial interface with the "Q" command
(request the weight data immediately) at an adjustable interval, plots the
mass live and streams every reading to a CSV file as it arrives.

Requires pyserial (pip install pyserial).

The serial settings must match the balance's "Serial interface (5if)"
function table settings. The factory settings are 2400 bps, 7 data bits,
even parity, 1 stop bit, CR LF terminator, A&D standard data format.
"""

import csv
import datetime
import math
import os
import re
import sys
import threading
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

import serial
import serial.tools.list_ports

BAUD_RATES = [600, 1200, 2400, 4800, 9600, 19200]
DEFAULT_BAUD_RATE = 2400

# Label -> (data bits, parity), matching the balance's "btpr" setting
DATA_FORMATS = {
    "7 bits, even": (serial.SEVENBITS, serial.PARITY_EVEN),
    "7 bits, odd": (serial.SEVENBITS, serial.PARITY_ODD),
    "8 bits, none": (serial.EIGHTBITS, serial.PARITY_NONE),
}

TERMINATOR = b"\r\n"
REPLY_TIMEOUT = 3.0  # seconds to wait for the balance to answer a command

STABLE_HEADERS = ("ST", "WT", "QT", "S")
UNSTABLE_HEADERS = ("US", "SD")
OVERLOAD_HEADERS = ("OL", "SI")

# Matches the A&D standard, DP, KF, MT, NU and CSV data formats, e.g.
#   "ST,+012.0078  g"   "WT   +12.0078  g"   "+   12.0078 g"
#   "S     12.0078 g"   "+012.0078"          "ST,+012.0078,  g"
READING_PATTERN = re.compile(
    r"^(?:(ST|US|OL|WT|QT|S\s?D|S\s?I|S)\b\s*,?)?\s*"
    r"([+-]?)\s*(\d+(?:\.\d+)?)\s*,?\s*"
    r"([A-Za-z%][A-Za-z% ]*)?$"
)


def parse_reading(line):
    """Parse one line of weight data.

    Returns (mass, unit, status) where status is "stable", "unstable",
    "overload" or "unknown" (mass is NaN on overload), or None if the line
    is not weight data (e.g. an acknowledge or error code).
    """
    text = line.replace("\x06", "").strip()
    if not text:
        return None

    compact = text.replace(" ", "")
    if (
        compact.startswith(OVERLOAD_HEADERS)
        or "E+19" in compact
        or compact in ("E", "-E", "H", "L")
        or compact.lstrip("+-") == "99999999"
    ):
        return math.nan, "", "overload"

    match = READING_PATTERN.match(text)
    if match is None:
        return None

    header = (match.group(1) or "").replace(" ", "")
    mass = float(match.group(2) + match.group(3))
    unit = (match.group(4) or "").replace(" ", "")

    if header in STABLE_HEADERS:
        status = "stable"
    elif header in UNSTABLE_HEADERS:
        status = "unstable"
    else:
        status = "unknown"
    return mass, unit, status


class MassTrackerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mass Tracker")

        self.balance = None
        self.serialLock = threading.Lock()
        self.connected = False
        self.running = False
        self.readThread = None
        self.csvFile = None
        self.csvWriter = None
        self.startTime = None
        self.nextSampleTime = None
        self.initialMass = None
        self.timeData = []
        self.massData = []
        self.changeData = []

        self._build_ui()
        self.refresh_ports()

        self.uiTimer = QTimer(self)
        self.uiTimer.setInterval(200)
        self.uiTimer.timeout.connect(self._update_status_labels)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        # --- connection row ---
        connRow = QtWidgets.QHBoxLayout()

        connRow.addWidget(QtWidgets.QLabel("Port:"))
        self.portCombo = QtWidgets.QComboBox()
        self.portCombo.setMinimumWidth(220)
        connRow.addWidget(self.portCombo)
        self.refreshButton = QtWidgets.QPushButton("Refresh")
        self.refreshButton.clicked.connect(self.refresh_ports)
        connRow.addWidget(self.refreshButton)

        connRow.addWidget(QtWidgets.QLabel("Baud rate:"))
        self.baudCombo = QtWidgets.QComboBox()
        for baudRate in BAUD_RATES:
            self.baudCombo.addItem(str(baudRate), baudRate)
        self.baudCombo.setCurrentIndex(BAUD_RATES.index(DEFAULT_BAUD_RATE))
        connRow.addWidget(self.baudCombo)

        connRow.addWidget(QtWidgets.QLabel("Data bits, parity:"))
        self.formatCombo = QtWidgets.QComboBox()
        self.formatCombo.addItems(DATA_FORMATS.keys())
        connRow.addWidget(self.formatCombo)

        self.connectButton = QtWidgets.QPushButton("Connect Balance")
        self.connectButton.clicked.connect(self.toggle_connect)
        self.connectionLabel = QtWidgets.QLabel("Not connected")
        connRow.addWidget(self.connectButton)
        connRow.addWidget(self.connectionLabel)
        connRow.addStretch()
        layout.addLayout(connRow)

        # --- settings row ---
        settingsRow = QtWidgets.QHBoxLayout()

        settingsRow.addWidget(QtWidgets.QLabel("Interval (s):"))
        self.intervalSpin = QtWidgets.QDoubleSpinBox()
        self.intervalSpin.setRange(0.5, 3600.0)
        self.intervalSpin.setDecimals(1)
        self.intervalSpin.setSingleStep(0.5)
        self.intervalSpin.setValue(5.0)
        settingsRow.addWidget(self.intervalSpin)

        settingsRow.addWidget(QtWidgets.QLabel("CSV file:"))
        self.csvPathEdit = QtWidgets.QLineEdit(self._default_csv_path())
        settingsRow.addWidget(self.csvPathEdit, stretch=1)
        self.browseButton = QtWidgets.QPushButton("Browse...")
        self.browseButton.clicked.connect(self.choose_csv_path)
        settingsRow.addWidget(self.browseButton)

        layout.addLayout(settingsRow)

        # --- start/stop row ---
        controlRow = QtWidgets.QHBoxLayout()
        self.startStopButton = QtWidgets.QPushButton("Start Tracking")
        self.startStopButton.clicked.connect(self.toggle_tracking)
        controlRow.addWidget(self.startStopButton)

        self.reZeroButton = QtWidgets.QPushButton("Re-zero")
        self.reZeroButton.setEnabled(False)
        self.reZeroButton.clicked.connect(self.re_zero)
        controlRow.addWidget(self.reZeroButton)

        self.elapsedLabel = QtWidgets.QLabel("Elapsed: 0.0 s")
        self.nextSampleLabel = QtWidgets.QLabel("Next sample: -")
        self.currentValueLabel = QtWidgets.QLabel("Mass: -")
        self.currentChangeLabel = QtWidgets.QLabel("Change: -")
        controlRow.addWidget(self.elapsedLabel)
        controlRow.addWidget(self.nextSampleLabel)
        controlRow.addWidget(self.currentValueLabel)
        controlRow.addWidget(self.currentChangeLabel)
        controlRow.addStretch()
        layout.addLayout(controlRow)

        # --- plots ---
        self.plotTabs = QtWidgets.QTabWidget()

        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setLabel("bottom", "Time", units="s")
        self.plotWidget.setLabel("left", "Mass")
        self.plotWidget.showGrid(x=True, y=True)
        self.curve = self.plotWidget.plot(pen=pg.mkPen(color="y", width=2))
        self.plotTabs.addTab(self.plotWidget, "Mass")

        self.changePlotWidget = pg.PlotWidget()
        self.changePlotWidget.setLabel("bottom", "Time", units="s")
        self.changePlotWidget.setLabel("left", "Mass change")
        self.changePlotWidget.showGrid(x=True, y=True)
        self.changeCurve = self.changePlotWidget.plot(pen=pg.mkPen(color="c", width=2))
        self.plotTabs.addTab(self.changePlotWidget, "Mass change")

        layout.addWidget(self.plotTabs, stretch=1)

        self.setCentralWidget(central)
        self.resize(1000, 600)

    def _default_csv_path(self):
        scriptDir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(scriptDir, f"mass_{timestamp}.csv")

    def choose_csv_path(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose CSV output file", self.csvPathEdit.text(), "CSV files (*.csv)"
        )
        if path:
            self.csvPathEdit.setText(path)

    def refresh_ports(self):
        current = self.portCombo.currentData()
        self.portCombo.clear()
        for port in sorted(serial.tools.list_ports.comports()):
            self.portCombo.addItem(f"{port.device} - {port.description}", port.device)
        index = self.portCombo.findData(current)
        if index >= 0:
            self.portCombo.setCurrentIndex(index)

    # --- balance communication ---

    def _send_command(self, command):
        self.balance.write(command.encode("ascii") + TERMINATOR)
        self.balance.flush()

    def _query_mass(self):
        """Send "Q" and return (mass, unit, status) from the balance's reply."""
        with self.serialLock:
            self.balance.reset_input_buffer()
            self._send_command("Q")
            deadline = time.monotonic() + REPLY_TIMEOUT
            lastLine = ""
            while time.monotonic() < deadline:
                # Both terminator settings (CR LF and CR) contain a CR
                raw = self.balance.read_until(b"\r")
                if not raw:
                    continue
                lastLine = raw.decode("ascii", errors="replace").strip()
                reading = parse_reading(lastLine)
                if reading is not None:
                    return reading
        if lastLine:
            raise RuntimeError(f"Unexpected reply from balance: {lastLine!r}")
        raise RuntimeError(
            "No reply from balance. Check the cable, the COM port and that the baud rate "
            "and data bits/parity match the balance's serial interface settings."
        )

    def _set_connection_widgets_enabled(self, enabled):
        self.portCombo.setEnabled(enabled)
        self.refreshButton.setEnabled(enabled)
        self.baudCombo.setEnabled(enabled)
        self.formatCombo.setEnabled(enabled)

    def toggle_connect(self):
        if self.connected:
            self.disconnect_device()
        else:
            self.connect_device()

    def connect_device(self):
        try:
            portName = self.portCombo.currentData()
            if not portName:
                raise RuntimeError("No serial port selected (is the balance plugged in?)")
            dataBits, parity = DATA_FORMATS[self.formatCombo.currentText()]
            self.balance = serial.Serial(
                port=portName,
                baudrate=self.baudCombo.currentData(),
                bytesize=dataBits,
                parity=parity,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.5,
                write_timeout=2.0,
            )
            # Take a test reading to confirm the balance is answering
            mass, unit, status = self._query_mass()
            self.connected = True
            self.connectionLabel.setText(f"Connected ({portName})")
            self.connectButton.setText("Disconnect Balance")
            self._set_connection_widgets_enabled(False)
            self.reZeroButton.setEnabled(True)
            self._show_current_mass(mass, unit, status)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection error", str(exc))
            if self.balance is not None:
                try:
                    self.balance.close()
                except Exception:
                    pass
            self.balance = None
            self.connected = False

    def disconnect_device(self):
        if self.running:
            self.stop_tracking()
        if self.balance is not None:
            try:
                self.balance.close()
            except Exception:
                pass
        self.balance = None
        self.connected = False
        self.connectionLabel.setText("Not connected")
        self.connectButton.setText("Connect Balance")
        self._set_connection_widgets_enabled(True)
        self.reZeroButton.setEnabled(False)

    def re_zero(self):
        if not self.connected:
            return
        try:
            with self.serialLock:
                self._send_command("R")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Re-zero error", str(exc))

    # --- tracking control ---

    def toggle_tracking(self):
        if self.running:
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if not self.connected:
            self.connect_device()
            if not self.connected:
                return

        csvPath = self.csvPathEdit.text().strip()
        if not csvPath:
            QtWidgets.QMessageBox.warning(self, "No CSV path", "Please choose a CSV output file first.")
            return

        try:
            self.csvFile = open(csvPath, "w", newline="")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "File error", f"Could not open CSV file:\n{exc}")
            return

        self.csvWriter = csv.writer(self.csvFile)
        self.csvWriter.writerow(["Timestamp", "Elapsed_s", "Mass", "Unit", "Status", "Mass_change"])
        self.csvFile.flush()

        self.initialMass = None
        self.timeData = []
        self.massData = []
        self.changeData = []
        self.curve.setData(self.timeData, self.massData)
        self.changeCurve.setData(self.timeData, self.changeData)

        self.interval = self.intervalSpin.value()
        self.startTime = time.monotonic()
        self.nextSampleTime = self.startTime

        self.running = True
        self.stopRequested = False
        self.intervalSpin.setEnabled(False)
        self.csvPathEdit.setEnabled(False)
        self.browseButton.setEnabled(False)
        self.startStopButton.setText("Stop Tracking")

        self.readThread = threading.Thread(target=self._read_loop, daemon=True)
        self.readThread.start()
        self.uiTimer.start()

    def stop_tracking(self):
        self.stopRequested = True
        self.running = False
        if (
            self.readThread is not None
            and self.readThread.is_alive()
            and self.readThread is not threading.current_thread()
        ):
            self.readThread.join(timeout=REPLY_TIMEOUT + 1.0)
        self.uiTimer.stop()

        if self.csvFile is not None:
            self.csvFile.close()
            self.csvFile = None
            self.csvWriter = None

        self.intervalSpin.setEnabled(True)
        self.csvPathEdit.setEnabled(True)
        self.browseButton.setEnabled(True)
        self.startStopButton.setText("Start Tracking")
        self.nextSampleLabel.setText("Next sample: -")

    def _read_loop(self):
        while not self.stopRequested:
            try:
                mass, unit, status = self._query_mass()
            except Exception as exc:
                if not self.stopRequested:
                    QtCore.QMetaObject.invokeMethod(
                        self, "_handle_read_error", Qt.QueuedConnection, QtCore.Q_ARG(str, str(exc))
                    )
                break

            elapsed = time.monotonic() - self.startTime
            timestamp = datetime.datetime.now().isoformat()
            QtCore.QMetaObject.invokeMethod(
                self,
                "_handle_new_reading",
                Qt.QueuedConnection,
                QtCore.Q_ARG(float, elapsed),
                QtCore.Q_ARG(float, mass),
                QtCore.Q_ARG(str, unit),
                QtCore.Q_ARG(str, status),
                QtCore.Q_ARG(str, timestamp),
            )

            self.nextSampleTime += self.interval
            while not self.stopRequested and time.monotonic() < self.nextSampleTime:
                time.sleep(min(0.1, max(0.0, self.nextSampleTime - time.monotonic())))

    def _show_current_mass(self, mass, unit, status):
        if math.isnan(mass):
            self.currentValueLabel.setText("Mass: overload")
        else:
            self.currentValueLabel.setText(f"Mass: {mass:.4f} {unit} ({status})")

    @QtCore.pyqtSlot(float, float, str, str, str)
    def _handle_new_reading(self, elapsed, mass, unit, status, timestamp):
        self._show_current_mass(mass, unit, status)

        if math.isnan(mass):
            # Overload: log it, but leave it off the plots
            if self.csvWriter is not None:
                self.csvWriter.writerow([timestamp, f"{elapsed:.3f}", "", unit, status, ""])
                self.csvFile.flush()
            return

        if self.initialMass is None:
            self.initialMass = mass
            if unit:
                self.plotWidget.setLabel("left", f"Mass ({unit})")
                self.changePlotWidget.setLabel("left", f"Mass change ({unit})")
        massChange = mass - self.initialMass

        self.timeData.append(elapsed)
        self.massData.append(mass)
        self.changeData.append(massChange)
        self.curve.setData(self.timeData, self.massData)
        self.changeCurve.setData(self.timeData, self.changeData)
        self.currentChangeLabel.setText(f"Change: {massChange:+.4f} {unit}")

        if self.csvWriter is not None:
            self.csvWriter.writerow([timestamp, f"{elapsed:.3f}", mass, unit, status, f"{massChange:.4f}"])
            self.csvFile.flush()

    @QtCore.pyqtSlot(str)
    def _handle_read_error(self, message):
        self.stop_tracking()
        QtWidgets.QMessageBox.critical(self, "Balance read error", message)

    def _update_status_labels(self):
        if not self.running:
            return
        elapsed = time.monotonic() - self.startTime
        self.elapsedLabel.setText(f"Elapsed: {elapsed:.1f} s")
        remaining = max(0.0, self.nextSampleTime - time.monotonic())
        self.nextSampleLabel.setText(f"Next sample: {remaining:.1f} s")

    def closeEvent(self, event):
        self.disconnect_device()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MassTrackerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
