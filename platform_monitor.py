from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import jasco2080
import time
import datetime
import os
import math
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

        # Pump configuration will be loaded on demand via set_configuration() button.
        self.pump_widgets = []
        self.pump_names = []
        self.correction_factors = {}
        
        # Logging timer (interval in milliseconds).
        self.logging_interval = 10 * 1000
        self.temp_logger = QtCore.QTimer(self)
        self.temp_logger.timeout.connect(self.continuous_log_function, QtCore.Qt.UniqueConnection)
        self.temp_logger.start(self.logging_interval)

        # Rolling in-memory buffers for plotting.
        self._max_points = 300 # Plot history length cap for UI responsiveness.
        self._time_series = [] # Shared x-axis: elapsed time [min].
        self._temp_series_value = []
        self._pump_flow_series = {}  # Flow data per pump (initialized after pump config).
        self._pump_pressure_series = {}  # Pressure data per pump (initialized after pump config).
        self._flow_cumulative_value = []
        self._log_dataframe = pd.DataFrame()  # In-memory table mirrored to CSV on each cycle.
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

        # Pressure plot - pump curves will be added after set_configuration()
        self.pressure_plot = pg.PlotWidget(title="Pump Pressure")
        self.pressure_plot.setLabel("left", "Pressure", units="bar")
        self.pressure_plot.setLabel("bottom", "Time", units="min")
        self.pressure_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pressure_curves = {}  # Dict of {pump_name: curve}, populated by set_configuration()
        self.layout.addWidget(self.pressure_plot, 0, 1)

        # Flowrate plot - pump curves will be added after set_configuration()
        self.flowrate_plot = pg.PlotWidget(title="Pump Flowrate")
        self.flowrate_plot.setLabel("left", "Flow Rate", units="mL/min")
        self.flowrate_plot.setLabel("bottom", "Time", units="min")
        self.flowrate_plot.showGrid(x=True, y=True, alpha=0.3)
        self.flow_curves = {}  # Dict of {pump_name: curve}, populated by set_configuration()
        self.flow_curve_cumulative = None  # Initialized by set_configuration()
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

    def _get_platform_pumps(self):
        """Get pump list from Platform Control. Returns list of pump widgets or empty list."""
        if self.main is None or not hasattr(self.main, 'controller'):
            return []
        controller = self.main.controller
        if hasattr(controller, 'pump_widgets'):
            return controller.pump_widgets
        return []

    def _setup_pump_plots(self):
        """Create/recreate pump-specific plot curves based on current pump_names."""
        colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#F0E442"]
        
        # Clear old curves from plots
        for curve in self.pressure_curves.values():
            self.pressure_plot.removeItem(curve)
        for curve in self.flow_curves.values():
            self.flowrate_plot.removeItem(curve)
        if self.flow_curve_cumulative is not None:
            self.flowrate_plot.removeItem(self.flow_curve_cumulative)
        
        self.pressure_curves.clear()
        self.flow_curves.clear()
        
        # Create new curves for each pump
        for i, pump_name in enumerate(self.pump_names):
            color = colors[i % len(colors)]
            self.pressure_curves[pump_name] = self.pressure_plot.plot([], [], pen=pg.mkPen(color=color, width=2), name=pump_name)
            self.flow_curves[pump_name] = self.flowrate_plot.plot([], [], pen=pg.mkPen(color=color, width=2), name=pump_name)
        
        # Add cumulative flow curve
        self.flow_curve_cumulative = self.flowrate_plot.plot([], [], pen=pg.mkPen(color="#000000", width=2, style=QtCore.Qt.DashLine), name="Cumulative")
        
        # Add legends if there are pumps
        if self.pump_names:
            self.pressure_plot.addLegend()
            self.flowrate_plot.addLegend()

    def set_configuration(self):
        """Load pump configuration from Platform Control and initialize plots."""
        self.pump_widgets = self._get_platform_pumps()
        
        if not self.pump_widgets:
            QtWidgets.QMessageBox.warning(self, "No Pumps", "No pumps configured in Platform Control.")
            return
        
        # Extract pump names and initialize correction factors
        self.pump_names = [pw.nameEdit.text().strip() or f"Pump_{i}" for i, pw in enumerate(self.pump_widgets)]
        self.correction_factors = {name: 1.0 for name in self.pump_names}
        
        # Recreate plot curves
        self._setup_pump_plots()
        
        # Clear buffers and reinitialize for new pump set
        self._time_series = []
        self._temp_series_value = []
        self._pump_flow_series = {name: [] for name in self.pump_names}
        self._pump_pressure_series = {name: [] for name in self.pump_names}
        self._flow_cumulative_value = []
        
        # Log to console and show confirmation
        pump_list = ", ".join(self.pump_names)
        print(f"[Platform Monitor] Configured {len(self.pump_names)} pump(s): {pump_list}")
        QtWidgets.QMessageBox.information(
            self, 
            "Configuration Updated", 
            f"Configured {len(self.pump_names)} pump(s):\n{pump_list}"
        )

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



    def _update_plot(self, now, temp, pump_flows, pump_pressures):
        """Append latest values to buffers and refresh all plot curves.
        
        Args:
            now: datetime object of measurement time
            temp: temperature value
            pump_flows: dict {pump_name: flow_value}
            pump_pressures: dict {pump_name: pressure_value}
        """
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Append new sample to the shared time axis and temperature series.
        self._time_series.append(elapsed_time)
        self._temp_series_value.append(temp)

        # Keep all series the same length when max history is reached.
        if len(self._time_series) > self._max_points:
            self._time_series = self._time_series[-self._max_points:]
            self._temp_series_value = self._temp_series_value[-self._max_points:]
            for pump_name in self.pump_names:
                self._pump_flow_series[pump_name] = self._pump_flow_series[pump_name][-self._max_points:]
                self._pump_pressure_series[pump_name] = self._pump_pressure_series[pump_name][-self._max_points:]
            self._flow_cumulative_value = self._flow_cumulative_value[-self._max_points:]
        
        self.temp_curve.setData(self._time_series, self._temp_series_value)
        
        # Append pressure and flow for each pump.
        cumulative_flow = 0.0
        for pump_name in self.pump_names:
            pressure_val = pump_pressures.get(pump_name, float('NaN'))
            flow_val = pump_flows.get(pump_name, float('NaN'))
            
            self._pump_pressure_series[pump_name].append(pressure_val)
            self.pressure_curves[pump_name].setData(self._time_series, self._pump_pressure_series[pump_name])
            
            # Apply correction factor to flow for display
            corrected_flow = flow_val * self.correction_factors[pump_name] if not math.isnan(flow_val) else float('NaN')
            self._pump_flow_series[pump_name].append(corrected_flow)
            self.flow_curves[pump_name].setData(self._time_series, self._pump_flow_series[pump_name])
            
            if not math.isnan(flow_val):
                cumulative_flow += flow_val
        
        self._flow_cumulative_value.append(cumulative_flow)
        if self.flow_curve_cumulative is not None:
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






    def continuous_log_function(self, event=None):
        """Periodic acquisition + plot update + append to experiment log CSV for all configured pumps."""
        # set up directory and filename for logging - creates new file for each run with timestamp in name, stored in Experimental_logs folder.
        log_dir = "Experimental_logs"
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f"Experimental_log_{self.start_time_str}.csv")

        temp = self.safe_read_temp()
        now = datetime.datetime.now()
        elapsed_time = (now - self.start_time_int).total_seconds() / 60.0
        
        # Read flow and pressure from all configured pumps.
        pump_flows = {}  # {pump_name: flow_value}
        pump_pressures = {}  # {pump_name: pressure_value}
        
        for i, pump_widget in enumerate(self.pump_widgets): # goes through each pump widget in the platform control tab, reads flow and pressure, and stores in dicts with pump names as keys. Uses try-except to handle read errors gracefully.
            pump_name = self.pump_names[i]
            
            # Read flow
            try:
                flow_result = pump_widget.read_flow()
                pump_flows[pump_name] = float(flow_result or 0.0)
            except Exception as e:
                print(f"[Warning] Failed to read flow from {pump_name}: {type(e).__name__}: {e}")
                pump_flows[pump_name] = float('NaN')
            
            # Read pressure
            print(f"Methods inside {pump_name}:")
            for method in dir(pump_widget):
                if "press" in method.lower() or "read" in method.lower():
                    print(f" -> Found: {method}")
            try:
                pressure_result = pump_widget.read_pressure()
                pump_pressures[pump_name] = float(pressure_result or 0.0)
            except Exception as e:
                print(f"[Warning] Failed to read pressure from {pump_name}: {type(e).__name__}: {e}")
                pump_pressures[pump_name] = float('NaN')

        self._update_plot(now, temp, pump_flows, pump_pressures)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Apply correction factors and build CSV row data.
        corrected_flows = {} # create dict to hold corrected flow values for each pump - 
        # either add a correction factor to each pump manually or add it within GUI - probably best for correction here manually (less work)
        cumulative_flow = 0.0 # initial value for total flow across all pumps, is updated in the loop below and stored in the CSV for each timepoint to track cumulative flow over time.
        
        for pump_name in self.pump_names: # flow loop over pump variables in pump_names list
            flow_val = pump_flows.get(pump_name, float('NaN'))
            try:
                corrected = flow_val * self.correction_factors[pump_name] if not math.isnan(flow_val) else float('NaN') # apply correction factor to raw flow value, if flow_val is NaN then corrected is also set to NaN to avoid propagating invalid data through calculations and plots.
            except (TypeError, ValueError):
                corrected = float('NaN')
            corrected_flows[pump_name] = corrected
            if not math.isnan(corrected):
                cumulative_flow += corrected

        # Build one-row dataframe entry with dynamic pump columns.
        row_data = {
            "Time": timestamp,
            "Elapsed Time": round(elapsed_time, 2),
            "Temperature": temp,
            "Cumulative Flow": cumulative_flow,
            "Event": event,
            "residence_time": None
        }
        
        # Add flow and pressure columns for each pump.
        for pump_name in self.pump_names:
            row_data[f"Flow_{pump_name}"] = corrected_flows[pump_name]
            row_data[f"Pressure_{pump_name}"] = pump_pressures.get(pump_name, float('NaN'))
        
        df_entry = pd.DataFrame([row_data])

        # Check if file exists and ensure schema can grow when pumps are initialized later.
        file_exists = os.path.isfile(log_path)
        if file_exists:
            try:
                existing_columns = list(pd.read_csv(log_path, nrows=0).columns)
            except Exception as e:
                print(f"[Warning] Could not read existing log header: {type(e).__name__}: {e}")
                existing_columns = []

            if existing_columns:
                target_columns = existing_columns + [col for col in df_entry.columns if col not in existing_columns]

                # If new columns appear (e.g., Flow_/Pressure_ after set_configuration),
                # rewrite existing file with expanded header so new data is visible in CSV.
                if target_columns != existing_columns:
                    try:
                        existing_df = pd.read_csv(log_path)
                        for col in target_columns:
                            if col not in existing_df.columns:
                                existing_df[col] = pd.NA
                        existing_df = existing_df.reindex(columns=target_columns)
                        existing_df.to_csv(log_path, index=False)
                        print(f"[Platform Monitor] Log schema expanded with new columns: {', '.join([c for c in target_columns if c not in existing_columns])}")
                    except Exception as e:
                        print(f"[Warning] Failed to expand log schema: {type(e).__name__}: {e}")

                df_entry = df_entry.reindex(columns=target_columns)

        # Append to CSV - creates new file with header if it doesn't exist, otherwise appends without header.
        df_entry.to_csv(log_path, mode='a', index=False, header=not file_exists)

        # Update In-Memory DataFrame for the 'Export' button
        if not hasattr(self, '_log_dataframe') or self._log_dataframe is None:
            self._log_dataframe = df_entry
        else:
            self._log_dataframe = pd.concat([self._log_dataframe, df_entry], ignore_index=True)





