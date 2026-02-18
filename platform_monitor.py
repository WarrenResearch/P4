from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import jasco2080
import time
import datetime
import os
import pandas as pd
import pumpWidget as pw

"""
Platform monitor (tab 5) for live process readout and logging.

Signals monitored:
- Temperature from the furnace thermocouple (Modbus read)
- Individual pump flow rates
- Cumulative flow rate
- Pump pressures
- Placeholders for derived metrics (e.g., residence time)
"""


class PlatformMonitor(QtWidgets.QWidget):
    """Live plotting + periodic CSV logging for key platform process variables."""

    def __init__(self, parent=None, main=None):
        super(PlatformMonitor, self).__init__(parent)
        self.main = main

        self.layout = QtWidgets.QGridLayout(self)

        # Reference the thermocontroller instance from Platform Control (shared connection).
        self.a = 10 # Temperature correction factor (thermocouple -> external reference).
        self.start_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # Used in log filename.
        self.start_time_int = datetime.datetime.now() # Used to calculate elapsed time in minutes.

        # Pump widgets used for flow/pressure readback in this monitor.
        self.pump1 = pw.PumpControl(self, pumpName="Pump 1")
        self.pump2 = pw.PumpControl(self, pumpName="Pump 2")
        # Per-pump scaling for calibration compensation.
        self.pump1_correction_factor_x_value = 1
        self.pump2_correction_factor_x_value = 1
        
        # Logging timer (interval in milliseconds).
        self.logging_interval = 60 * 1000
        self.temp_logger = QtCore.QTimer(self)
        self.temp_logger.timeout.connect(self.continuous_log_function, QtCore.Qt.UniqueConnection)
        self.temp_logger.start(self.logging_interval)

        # Rolling in-memory buffers for plotting.
        self._max_points = 300 # Plot history length cap for UI responsiveness.
        self._time_series = [] # Shared x-axis: elapsed time [min].
        self._temp_series_value = [] 
        self._pressure_pump1_value = []
        self._pressure_pump2_value = []
        self._flow_pump1_value = []
        self._flow_pump2_value = []
        self._flow_cumulative_value = []
        self._log_dataframe = pd.DataFrame()  # In-memory table mirrored to CSV on each cycle.
        self._csv_initialized = False
        self._build_graphs()

        

    
    def _build_graphs(self):
        """Create plots and user controls for the monitor tab."""
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
    def safe_read_temp(self):
        """Read temperature with retry logic to avoid transient Modbus failures."""
        # Access the shared thermocontroller from Platform Control tab.
        if self.main is None or not hasattr(self.main, 'controller'):
            return float('nan')
        
        thermo_widget = getattr(self.main.controller, 'thermocontroller', None)
        if thermo_widget is None:
            return float('nan')
        
        thermo_obj = getattr(thermo_widget, 'thermocontrollerObj', None)
        if thermo_obj is None:
            return float('nan')
        
        # Retry logic for Modbus communication.
        for attempt in range(3):
            try:
                return thermo_obj.indicated() / self.a
            except Exception as e: 
               if attempt == 2:  # Only warn on final attempt
                   print(f"[Warning] Temperature read failed after 3 attempts: {e}")
               time.sleep(1)
        return float('nan')



    def update_logging_interval(self, value):
        """Update timer interval from UI value in seconds."""
        self.logging_interval = value * 1000
        self.temp_logger.setInterval(self.logging_interval)
        print(f"Logging interval updated to {value} seconds")



    def _update_plot(self, now, temp, pressure_pump1, pressure_pump2, flow_pump1, flow_pump2):
        """Append latest values to buffers and refresh all plot curves."""
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Append new sample to the shared time axis and temperature series.
        self._time_series.append(elapsed_time)
        self._temp_series_value.append(temp)

        # Keep all series the same length when max history is reached.
        if len(self._time_series) > self._max_points:
            self._time_series = self._time_series[-self._max_points:]
            self._temp_series_value = self._temp_series_value[-self._max_points:]
            self._pressure_pump1_value = self._pressure_pump1_value[-self._max_points:]
            self._pressure_pump2_value = self._pressure_pump2_value[-self._max_points:]
            self._flow_pump1_value = self._flow_pump1_value[-self._max_points:]
            self._flow_pump2_value = self._flow_pump2_value[-self._max_points:]
            self._flow_cumulative_value = self._flow_cumulative_value[-self._max_points:]
        self.temp_curve.setData(self._time_series, self._temp_series_value)
        
        # Pressure series (one per pump) plotted against shared time axis.
        self._pressure_pump1_value.append(pressure_pump1)
        self._pressure_pump2_value.append(pressure_pump2)
        self.pressure_curve_pump1.setData(self._time_series, self._pressure_pump1_value)
        self.pressure_curve_pump2.setData(self._time_series, self._pressure_pump2_value)
        
        # Flow series and cumulative flow, all against shared time axis.
        cumulative_flow = flow_pump1 + flow_pump2   
        self._flow_pump1_value.append(flow_pump1*self.pump1_correction_factor_x_value)
        self._flow_pump2_value.append(flow_pump2*self.pump2_correction_factor_x_value)
        self._flow_cumulative_value.append(cumulative_flow)
        self.flow_curve_pump1.setData(self._time_series, self._flow_pump1_value)
        self.flow_curve_pump2.setData(self._time_series, self._flow_pump2_value)
        self.flow_curve_cumulative.setData(self._time_series, self._flow_cumulative_value)

    def export_data(self):
        """Export accumulated in-memory log data to a user-selected CSV file."""
        if self._log_dataframe.empty:
            QtWidgets.QMessageBox.warning(self, "No Data", "No data to export yet.")
            return
        

        # testing 
      

        #  file_path, _ = QtWidgets.QFileDialog.getSaveFileName( '''uncoment after testing'''
            #self,
            #"Export Platform Data",
            #f"experiment_data_{self.start_time_str}.csv",
            #"CSV Files (*.csv)"
            #)
        
        #if file_path:
            #try:
                #self._log_dataframe.to_csv(file_path, index=False)
                #QtWidgets.QMessageBox.information(self, "Success", f"Data exported to {file_path}")
            #except Exception as e:
                #QtWidgets.QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")






    def continuous_log_function(self,event=None):
        """Periodic acquisition + plot update + append to experiment log CSV."""

        # set up directory and filename for logging - creates new file for each run with timestamp in name, stored in Experimental_logs folder.
        log_dir = "Experimental_logs"
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f"Experimental_log_{self.start_time_str}.csv")

        temp = self.safe_read_temp()
        now = datetime.datetime.now()
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Read pump values with independent error handling so one failure does not block logging.
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

        # Build one-row dataframe entry for this logging tick.
        df_entry = pd.DataFrame([{
            "Time": timestamp,
            "Elapsed Time": round(elapsed_time, 2),
            "Temperature": temp,
            "Step": getattr(self,"_sequence_index",None),
            "Flow_A": flow_pump1 * self.pump1_correction_factor_x_value,
            "Flow_B": flow_pump2 * self.pump2_correction_factor_x_value,
            "Cumulative Flow": cumulative_flow,
            "Pressure_A": pressure_pump1,
            "Pressure_B": pressure_pump2,
            "Event": event,
            "residence_time": None # placeholder for residence time calculation - implement as needed
        }])

        # Check if file exists to decide on header
        file_exists = os.path.isfile(log_path)
    
        # Append to CSV - creates new file with header if it doesn't exist, otherwise appends without header.
        df_entry.to_csv(log_path, mode='a', index=False, header=not file_exists)

        # 6. Update In-Memory DataFrame for the 'Export' button
        if not hasattr(self, '_log_dataframe') or self._log_dataframe is None:
            self._log_dataframe = df_entry
        else:
            self._log_dataframe = pd.concat([self._log_dataframe, df_entry], ignore_index=True)





