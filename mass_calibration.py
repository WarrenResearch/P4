import math
import os
import time

import numpy as np
import pandas as pd
import serial
import serial.tools.list_ports
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer

from mass_tracker import (
    BAUD_RATES,
    DATA_FORMATS,
    DEFAULT_BAUD_RATE,
    REPLY_TIMEOUT,
    TERMINATOR,
    parse_reading,
)

'''
designed for one pump at a time, do not use more than 1 - to test multiple pumps, run this script when connected to each pump separately.

same flowrate steps as droplet_calibration, but the pump outlet is collected on an A&D mass balance (see mass_tracker.py) and the
rate of mass change is used for the calibration instead of the droplet count

You will need to check self.reactor_volume is the correct volume for your calibration, and self.density_g_per_ml if you are not pumping water
'''


class BalanceSettingsDialog(QtWidgets.QDialog):
    """Asks which serial port the balance is on. Settings must match the balance's "5if" function table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mass balance connection")

        self.portCombo = QtWidgets.QComboBox()
        for port in sorted(serial.tools.list_ports.comports()):
            self.portCombo.addItem(f"{port.device} - {port.description}", port.device)

        self.baudCombo = QtWidgets.QComboBox()
        for baudRate in BAUD_RATES:
            self.baudCombo.addItem(str(baudRate), baudRate)
        self.baudCombo.setCurrentIndex(BAUD_RATES.index(DEFAULT_BAUD_RATE))

        self.formatCombo = QtWidgets.QComboBox()
        self.formatCombo.addItems(DATA_FORMATS.keys())

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QtWidgets.QFormLayout(self)
        form.addRow("Balance port:", self.portCombo)
        form.addRow("Baud rate:", self.baudCombo)
        form.addRow("Data bits, parity:", self.formatCombo)
        form.addRow(buttons)

    def settings(self):
        dataBits, parity = DATA_FORMATS[self.formatCombo.currentText()]
        return {
            "port": self.portCombo.currentData(),
            "baudrate": self.baudCombo.currentData(),
            "bytesize": dataBits,
            "parity": parity,
        }


class MassBalanceCalibration:
    def __init__(self, widget, port, baudrate=DEFAULT_BAUD_RATE, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN):
        if not port:
            raise RuntimeError("No serial port selected for the balance (is it plugged in?)")

        self.balance = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5,
            write_timeout=2.0,
        )
        # Take a test reading to confirm the balance is answering before the pump is started
        try:
            _, unit, _ = self.query_mass()
        except Exception:
            self.balance.close()
            raise
        if unit and unit != "g":
            print(f"WARNING: balance is reporting in '{unit}', calibration assumes grams")

        self.calibration_start_time = time.time()

        self.widget = widget # holds live reference to widget (so your calibration value goes to the correct place)
        self.reactor_volume_ml = 0.1 # change this with your volume, in my case im not using the whole reactor for the calibration
        self.density_g_per_ml = 1.0 # water: 1 mL/min should give 1 g over 1 minute

        # --- Experiment Settings ---
        self.flowrate_list = [0.1, 0.25, 0.5]
        self.runs_per_flowrate = 3
        self.maximum_duration_min = 3
        self.maximum_duration_s = self.maximum_duration_min * 60

        # --- State Tracking Indexes ---
        self.current_flow_idx = 0
        self.current_run_idx = 0
        self.aborted = False

        # --- Storage Structs ---
        self.master_records = []
        self.summary_averages = {flow: [] for flow in self.flowrate_list}

        # --- Timer Setup ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_mass)

        self.start_new_run()

    def query_mass(self):
        """Send "Q" and return (mass, unit, status) from the balance's reply."""
        self.balance.reset_input_buffer()
        self.balance.write(b"Q" + TERMINATOR)
        self.balance.flush()
        deadline = time.monotonic() + REPLY_TIMEOUT
        lastLine = ""
        while time.monotonic() < deadline:
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

    def start_new_run(self):
        current_flowrate = self.flowrate_list[self.current_flow_idx]

        print(f"\n setting flowrates and waiting for steady state...")
        self.widget.setFlowrateText.setText(str(current_flowrate))
        self.widget.setFlowrate()
        self.widget.start()

        if self.current_run_idx == 0:
            steady_state_minutes = 3 * (self.reactor_volume_ml / current_flowrate)
            steady_state_seconds = steady_state_minutes * 60

            QTimer.singleShot(int(steady_state_seconds*1000),self.activate_measurement_timer)
        else:
            self.activate_measurement_timer()

    def activate_measurement_timer(self):
        if self.aborted:
            return
        try:
            self.baseline_mass, _, _ = self.query_mass()
        except Exception as exc:
            self.abort(str(exc))
            return
        if math.isnan(self.baseline_mass):
            self.abort("Balance is overloaded, empty the collection vessel and start again")
            return

        self.start_time = time.time()
        self.mass_change = [0.0]
        self.timestamps = [0.0]
        self.timer.start(5000) # Poll every 5 seconds

    def poll_mass(self):
        try:
            mass, _, _ = self.query_mass()
        except Exception as exc:
            self.abort(str(exc))
            return
        duration = time.time() - self.start_time

        current_flowrate = self.flowrate_list[self.current_flow_idx]
        run_number = self.current_run_idx + 1

        if math.isnan(mass):
            print(f"[{current_flowrate} mL/min | Run {run_number}] Time: {duration:.0f}s, balance overloaded - reading skipped")
        else:
            relative_mass = mass - self.baseline_mass
            self.mass_change.append(relative_mass)
            self.timestamps.append(duration)
            print(f"[{current_flowrate} mL/min | Run {run_number}] Time: {duration:.0f}s, Mass: {relative_mass:.4f} g")

        #  Check if this specific run window is completed
        if duration >= self.maximum_duration_s:
            self.timer.stop()

            if len(self.timestamps) < 2:
                self.abort("Not enough balance readings to fit a mass gradient")
                return

            # Gradient of mass vs time for this specific run window, in g/min
            mass_rate = np.polyfit(self.timestamps, self.mass_change, 1)[0] * 60
            self.summary_averages[current_flowrate].append(mass_rate)

            print(f"-> Finished Run {run_number} (@ {current_flowrate} mL/min). Mass rate: {mass_rate:.4f} g/min")

            # Append the completed time-series data for this run into master records
            for ts, change in zip(self.timestamps, self.mass_change):
                self.master_records.append({
                    "Flowrate (mL/min)": current_flowrate,
                    "Run": run_number,
                    "Time (s)": round(ts, 1),
                    "Mass Change (g)": round(change, 4),
                    "Run Mass Rate (g/min)": round(mass_rate, 4)
                })

            # State Logic: Move to next run or next flowrate
            if self.current_run_idx < (self.runs_per_flowrate - 1):
                self.current_run_idx += 1
                self.start_new_run()
            else:
                # Calculate overall average for this completed flowrate block
                overall_avg = np.mean(self.summary_averages[current_flowrate])
                print(f"==> OVERALL AVERAGE FOR {current_flowrate} mL/min: {overall_avg:.4f} g/min <==")

                # Apply the final overall average back onto the records of this specific flowrate block
                for record in self.master_records:
                    if record["Flowrate (mL/min)"] == current_flowrate:
                        record["Overall Mass Rate (g/min)"] = round(overall_avg, 4)

                if self.current_flow_idx < (len(self.flowrate_list) - 1):
                    self.current_flow_idx += 1
                    self.current_run_idx = 0
                    self.start_new_run()
                else:
                    self.calibration_end_time = time.time()
                    total_calibration_time = self.calibration_end_time - self.calibration_start_time
                    print(f"\nCalibration complete! Total time: {total_calibration_time/60:.2f} minutes")
                    self.disconnect_hardware()

                    gradient = self.calibration_gradient()
                    if gradient <= 0:
                        print("No mass increase measured, calibration factor left unchanged")
                        self.save_master_csv()
                        return
                    calibration_factor = self.calibration_factor(gradient)

                    print(f"\nAll experiments complete! Master CSV saving...")
                    self.save_master_csv()

                    self.widget.save_calibration(calibration_factor, method="Mass balance")
                    print("Pump Calibrated with factor: ", calibration_factor)

    def save_master_csv(self):
        results_dir = 'calibration_results'
        os.makedirs(results_dir, exist_ok=True)
        timestamp_str = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(results_dir, f'mass_calibration_data_{timestamp_str}.csv')

        df = pd.DataFrame(self.master_records)
        df.to_csv(filepath, index=False, float_format='%.4f')
        print(f'Master CSV safely written to: {filepath}')

    def calibration_gradient(self):
        """Gradient of measured mass rate (g/min) vs set flowrate (mL/min), fitted through the origin."""
        x = np.array(list(self.summary_averages.keys()))
        y = np.array([np.mean(avgs_list) for avgs_list in self.summary_averages.values()])

        x = x[:,np.newaxis]
        gradient, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
        for record in self.master_records:
            record['Calibration Gradient'] = round(gradient[0],4)

        return gradient[0]

    def calibration_factor(self, gradient):
        expected_gradient = self.density_g_per_ml # g/min per mL/min
        correction_factor = expected_gradient / gradient
        for record in self.master_records:
            record['Calibration Factor'] = round(correction_factor,4)
        return correction_factor

    def abort(self, message):
        self.aborted = True
        self.timer.stop()
        print(f"Mass balance calibration aborted: {message}")
        self.disconnect_hardware()

    def disconnect_hardware(self):
        print("Disconnecting hardware...")
        try:
            self.balance.close()
        except Exception:
            pass
        self.widget.stop()
