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

        self.pump1 = pw.PumpControl(self, pumpName="Pump 1") # create pump control widget to read flowrate from pump 1 - adjust as needed for different pumps or flowrate retrieval methods
        self.pump2 = pw.PumpControl(self, pumpName="Pump 2") # create pump control widget to read flowrate from pump 2 - adjust as needed for different pumps or flowrate retrieval methods
        self.pump1_correction_factor_x_value = 1  # adjust if pump 1 has different calibration
        self.pump2_correction_factor_x_value = 1   # adjust if pump 2 has different calibration
        
        self.logging_interval = 60 * 1000 #every 60 seconds in ms (starts when the script is run)
        self.temp_logger = QtCore.QTimer()
        self.temp_logger.timeout.connect(self.continuous_log_function)
        self.temp_logger.start(self.logging_interval)

        self._max_points = 300 # used to limit number of points on plot for performance - adjust as needed (e.g. for 20s logging interval, 300 points = 100 minutes of data)
        self._temp_series_time = []
        self._temp_series_value = []
        self._pressure_pump1_time = []
        self._pressure_pump1_value = []
        self._pressure_pump2_time = []
        self._pressure_pump2_value = []
        self._flow_pump1_time = []
        self._flow_pump1_value = []
        self._flow_pump2_time = []
        self._flow_pump2_value = []
        self._flow_cumulative_time = []
        self._flow_cumulative_value = []
        self._log_dataframe = pd.DataFrame()  # store accumulated log data for export
        self._csv_initialized = False
        self._build_graphs()

        

    
    def _build_graphs(self):
        # Temperature plot
        self.temp_plot = pg.PlotWidget(title="Reactor Temperature")
        self.temp_plot.setLabel("left", "Temperature", units="C")
        self.temp_plot.setLabel("bottom", "Time", units="min")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)
        self.temp_curve = self.temp_plot.plot([], [], pen=pg.mkPen(color="#e4572e", width=2))
        self.layout.addWidget(self.temp_plot, 0, 0)

        # Pressure plot
        self.pressure_plot = pg.PlotWidget(title="Pump Pressure")
        self.pressure_plot.setLabel("left", "Pressure", units="bar")
        self.pressure_plot.setLabel("bottom", "Time", units="min")
        self.pressure_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pressure_curve_pump1 = self.pressure_plot.plot([], [], pen=pg.mkPen(color="#0072B2", width=2), name="Pump 1")
        self.pressure_curve_pump2 = self.pressure_plot.plot([], [], pen=pg.mkPen(color="#E69F00", width=2), name="Pump 2")
        self.pressure_plot.addLegend()
        self.layout.addWidget(self.pressure_plot, 0, 1)

        # Flowrate plot
        self.flowrate_plot = pg.PlotWidget(title="Pump Flowrate")
        self.flowrate_plot.setLabel("left", "Flow Rate", units="mL/min")
        self.flowrate_plot.setLabel("bottom", "Time", units="min")
        self.flowrate_plot.showGrid(x=True, y=True, alpha=0.3)
        self.flow_curve_pump1 = self.flowrate_plot.plot([], [], pen=pg.mkPen(color="#0072B2", width=2), name="Pump 1")
        self.flow_curve_pump2 = self.flowrate_plot.plot([], [], pen=pg.mkPen(color="#E69F00", width=2), name="Pump 2")
        self.flow_curve_cumulative = self.flowrate_plot.plot([], [], pen=pg.mkPen(color="#009E73", width=2, style=QtCore.Qt.DashLine), name="Cumulative")
        self.flowrate_plot.addLegend()
        self.layout.addWidget(self.flowrate_plot, 1, 0)

        # Add controls in bottom-right
        controls_widget = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls_widget)
        
        # Logging interval control
        interval_group = QtWidgets.QGroupBox("Logging Settings")
        interval_layout = QtWidgets.QHBoxLayout(interval_group)
        interval_label = QtWidgets.QLabel("Interval (sec):")
        self.logging_interval_spinbox = QtWidgets.QSpinBox()
        self.logging_interval_spinbox.setRange(1, 3600)
        self.logging_interval_spinbox.setValue(int(self.logging_interval / 1000))
        self.logging_interval_spinbox.setSuffix(" s")
        self.logging_interval_spinbox.valueChanged.connect(self.update_logging_interval)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.logging_interval_spinbox)
        controls_layout.addWidget(interval_group)
        
        # Export button
        self.export_button = QtWidgets.QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        controls_layout.addWidget(self.export_button)
        controls_layout.addStretch()
        
        self.layout.addWidget(controls_widget, 1, 1)

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

    def update_logging_interval(self, value):
        """Update the logging interval when spinbox value changes"""
        self.logging_interval = value * 1000  # Convert seconds to milliseconds
        self.temp_logger.setInterval(self.logging_interval)
        print(f"Logging interval updated to {value} seconds")



    def _update_plot(self, now, temp, pressure_pump1, pressure_pump2, flow_pump1, flow_pump2):
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Update temperature data
        self._temp_series_time.append(elapsed_time)
        self._temp_series_value.append(temp)
        if len(self._temp_series_time) > self._max_points:
            self._temp_series_time = self._temp_series_time[-self._max_points:]
            self._temp_series_value = self._temp_series_value[-self._max_points:]
        self.temp_curve.setData(self._temp_series_time, self._temp_series_value)
        
        # Update pressure data
        self._pressure_pump1_time.append(elapsed_time)
        self._pressure_pump1_value.append(pressure_pump1)
        self._pressure_pump2_time.append(elapsed_time)
        self._pressure_pump2_value.append(pressure_pump2)
        if len(self._pressure_pump1_time) > self._max_points:
            self._pressure_pump1_time = self._pressure_pump1_time[-self._max_points:]
            self._pressure_pump1_value = self._pressure_pump1_value[-self._max_points:]
            self._pressure_pump2_time = self._pressure_pump2_time[-self._max_points:]
            self._pressure_pump2_value = self._pressure_pump2_value[-self._max_points:]
        self.pressure_curve_pump1.setData(self._pressure_pump1_time, self._pressure_pump1_value)
        self.pressure_curve_pump2.setData(self._pressure_pump2_time, self._pressure_pump2_value)
        
        # Update flowrate data
        cumulative_flow = flow_pump1 + flow_pump2   
        self._flow_pump1_time.append(elapsed_time)
        self._flow_pump1_value.append(flow_pump1*self.pump1_correction_factor_x_value)
        self._flow_pump2_time.append(elapsed_time)
        self._flow_pump2_value.append(flow_pump2*self.pump2_correction_factor_x_value)
        self._flow_cumulative_time.append(elapsed_time)
        self._flow_cumulative_value.append(cumulative_flow)
        if len(self._flow_pump1_time) > self._max_points:
            self._flow_pump1_time = self._flow_pump1_time[-self._max_points:]
            self._flow_pump1_value = self._flow_pump1_value[-self._max_points:]
            self._flow_pump2_time = self._flow_pump2_time[-self._max_points:]
            self._flow_pump2_value = self._flow_pump2_value[-self._max_points:]
            self._flow_cumulative_time = self._flow_cumulative_time[-self._max_points:]
            self._flow_cumulative_value = self._flow_cumulative_value[-self._max_points:]
        self.flow_curve_pump1.setData(self._flow_pump1_time, self._flow_pump1_value)
        self.flow_curve_pump2.setData(self._flow_pump2_time, self._flow_pump2_value)
        self.flow_curve_cumulative.setData(self._flow_cumulative_time, self._flow_cumulative_value)

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
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Read pump data with error handling
        try:
            flow_pump1 = float(self.pump1.read_flow()) if hasattr(self.pump1, 'read_flow') else 0.0
        except (TypeError, ValueError, AttributeError) as e:
            print(f"[Warning] Failed to read flow from pump 1: {e}")
            flow_pump1 = float('NaN')
        
        try:
            flow_pump2 = float(self.pump2.read_flow()) if hasattr(self.pump2, 'read_flow') else 0.0
        except (TypeError, ValueError, AttributeError) as e:
            print(f"[Warning] Failed to read flow from pump 2: {e}")
            flow_pump2 = float('NaN')
        
        try:
            pressure_pump1 = float(self.pump1.read_pressure()) if hasattr(self.pump1, 'read_pressure') else 0.0
        except (TypeError, ValueError, AttributeError) as e:
            print(f"[Warning] Failed to read pressure from pump 1: {e}")
            pressure_pump1 = float('NaN')
        
        try:
            pressure_pump2 = float(self.pump2.read_pressure()) if hasattr(self.pump2, 'read_pressure') else 0.0
        except (TypeError, ValueError, AttributeError) as e:
            print(f"[Warning] Failed to read pressure from pump 2: {e}")
            pressure_pump2 = float('NaN')

        self._update_plot(now, temp, pressure_pump1, pressure_pump2, flow_pump1, flow_pump2)


        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cumulative_flow = flow_pump1 + flow_pump2

        df_entry = pd.DataFrame({
            "Time": timestamp,
            "Elapsed Time": elapsed_time,
            "Temperature": temp,
            "Step": getattr(self,"_sequence_index",None),
            "Flow_A": flow_pump1 * self.pump1_correction_factor_x_value,
            "Flow_B": flow_pump2 * self.pump2_correction_factor_x_value,
            "Cumulative Flow": cumulative_flow,
            "Pressure_A": pressure_pump1,
            "Pressure_B": pressure_pump2,
            "Event": event,
            "residence_time": None # placeholder for residence time calculation - implement as needed
        })

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





