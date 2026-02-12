from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import jasco2080
from thermocontroller_driver import Furnace
import time
import datetime
import os
import pandas as pd
import pumpWidget as pw

''' code for tab 5 - platform monitor, which will show live data from the platform, 
 and allow the user to monitor the state of the platform during an experiment 
 setup:
    - temperature: thermocouple read from furnace (via modbus)
    - individual flow rates: read from jasco pump
    - cumulative flow rates: sum of flow rates from jasco pump
    - pressure: read from jasco pump
    - residence time: calculated based on flow rates and reactor volume

 '''


class PlatformMonitor(QtWidgets.QWidget):
    def __init__(self, parent=None, main=None):
        super(PlatformMonitor, self).__init__(parent)
        self.main = main

        self.layout = QtWidgets.QGridLayout(self)

        self.thermo = Furnace() # create thermocontroller instance
        self.a = 10 # correction factor for temperature read (to match external thermometer) - adjust as needed
        self.start_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # string start time for log filename
        self.start_time_int = datetime.datetime.now() # datetime object for reaction time calculations
        self.elapsed_time = (datetime.datetime.now() - self.start_time_int).total_seconds() / 60.0


        self._max_points = 300 # used to limit number of points on plot for performance - adjust as needed (e.g. for 20s logging interval, 300 points = 100 minutes of data)
        self._temp_series_time = []
        self._temp_series_value = []
        self._log_dataframe = pd.DataFrame()  # store accumulated log data for export
        self._csv_initialized = False
        self._build_temperature_plot()

        self.logging_interval = 20 * 1000 #every 20 seconds in ms (starts when the script is run)
        self.temp_logger = QtCore.QTimer()
        self.temp_logger.timeout.connect(self.continuous_log_function)
        self.temp_logger.start(self.logging_interval)

        self.pump1 = pw.PumpControl(self, pumpName="Pump 1") # create pump control widget to read flowrate from pump 1 - adjust as needed for different pumps or flowrate retrieval methods
        self.pump2 = pw.PumpControl(self, pumpName="Pump 2") # create pump control widget to read flowrate from pump 2 - adjust as needed for different pumps or flowrate retrieval methods



    def _build_temperature_plot(self):
        self.temp_plot = pg.PlotWidget(title="Furnace Temperature")
        self.temp_plot.setLabel("left", "Temperature", units="C")
        self.temp_plot.setLabel("bottom", "Time", units="min")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temp_curve = self.temp_plot.plot([], [], pen=pg.mkPen(color="#e4572e", width=2))
        self.layout.addWidget(self.temp_plot, 0, 0)

        # Add export button
        self.export_button = QtWidgets.QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        self.layout.addWidget(self.export_button, 1, 0)

    ##### Temperature relies on furnace thermocouple 
    def safe_read_temp(self): # temperature read with retries - otherwise may throw error and stop program
        for attempt in range(3):
            try:
                return self.thermo.indicated() / self.a # read temperature and apply correction factor
            except Exception as e: 
               print(f"[Warning] Modbus read failed (attempt {attempt+1}/3): {e}") #log warning 
               time.sleep(1) # wait before retrying
        print("[Error] Failed to read temperature after 3 attempts — returning NaN.")
        return float('nan')



    def _update_plot(self, now, temp):
        elapsed_time = self.elapsed_time
        # Track a rolling window for plotting.
        self._temp_series_time.append(elapsed_time)
        self._temp_series_value.append(temp)
        if len(self._temp_series_time) > self._max_points:
            self._temp_series_time = self._temp_series_time[-self._max_points:]
            self._temp_series_value = self._temp_series_value[-self._max_points:]

        self.temp_curve.setData(self._temp_series_time, self._temp_series_value)

    def export_data(self):
        """Export accumulated log data to CSV with file dialog"""
        if self._log_dataframe.empty:
            QtWidgets.QMessageBox.warning(self, "No Data", "No data to export yet.")
            return
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Platform Data",
            f"experiment_data_{self.start_time_str}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                self._log_dataframe.to_csv(file_path, index=False)
                QtWidgets.QMessageBox.information(self, "Success", f"Data exported to {file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")


    def continuous_log_function(self,event=None): #logging function that runs every x seconds (set by self.logging_interval)
        log_dir = "Experimental_logs"
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"Experimental_log {self.start_time_str}.csv") #log path with start time in filename

        temp = self.safe_read_temp()

        now = datetime.datetime.now()

        elapsed_time = self.elapsed_time

        self._update_plot(now, temp)


        pump1_correction_factor_x_value = 1  # adjust if pump 1 has different calibration

        pump2_correction_factor_x_value = 1   # adjust if pump 2 has different calibration
        

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df_entry = pd.DataFrame([{
            "Time": timestamp,
            "Elapsed Time": elapsed_time,
            "Temperature": temp,
            "Step": getattr(self,"_sequence_index",None),
            "Flow_A": (float(self.pump1.read_flow())*pump1_correction_factor_x_value), # retrieves the text from the flowrate input box and applies correction factor
            "Flow_B": (float(self.pump2.read_flow())*pump2_correction_factor_x_value), # retrieves the text from the flowrate input box and applies correction factor
            "Event": event,
            "Pump 1 Pressure": self.pump1.read_pressure(), # placeholder for pressure read from pump - implement as needed
            "Pump 2 Pressure": self.pump2.read_pressure(), # placeholder for pressure read from pump - implement as needed
            "residence_time": None # placeholder for residence time calculation - implement as needed
        }])

        if not self._csv_initialized:
            df_entry.to_csv(log_path, index=False, mode='w')
            self._csv_initialized = True
            self._log_dataframe = df_entry.copy()
        else:
            df_entry.to_csv(log_path, index=False, mode='a', header=False)
            self._log_dataframe = pd.concat([self._log_dataframe, df_entry], ignore_index=True)
        
        with open(log_path, "a") as f:
            f.flush()
            os.fsync(f.fileno())





