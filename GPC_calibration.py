# PyQt5 preamble
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QLabel,
                             QCheckBox, QLineEdit, QGridLayout, QGroupBox, QFileDialog, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from PyQt5.QtGui import QColor

# Basic packages preamble
import pandas as pd
import numpy as np
import threading
import datetime
import os
import pickle
import PicoGPC
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# Import classes/functions from files
import GPC_handler



class GPC_calibration(QtWidgets.QWidget):
    def __init__(self, parent, main):
############################## PREAMBLE ##############################
        super().__init__(parent)
        self.red_shades = [QColor(139, 0, 0, 255 - i * 25) for i in range(10)]  # Dark red (139,0,0) to lighter
        self.main = main
        self.TC08connected = False
        # self.GPCValve = self.main.controller.valve5
        # Establish signal to a slot for GPC_handler to emit data to
        # self.gpc_handler = GPC_handler.GPC_handler(self, self, None)
        # self.gpc_handler.GPC_complete.connect(self.GPC_complete_callback)
        
############################## LAYOUT ##############################
        # Set the master layout of the Method tab onto which all widgets are placed
        self.Layout = QtWidgets.QGridLayout()
        self.setLayout(self.Layout)
        # Main groupBox for all input and calculated experimental parameters
        self.GPC_calibrateBox = QtWidgets.QGroupBox("GPC Calibration")
        self.GPC_calibrateBox.setMaximumSize(1800, 910)
        self.GPC_calibrateBox.setContentsMargins(10, 5, 10, 5)
        main_layout = QHBoxLayout()

        # Left section for table and buttons
        left_layout = QVBoxLayout()
        # Table
        self.GPCcalibtable = QTableWidget(0, 6)
        self.GPCcalibtable.setHorizontalHeaderLabels(["Residence Time", "Log(MW)", "MW", "RT1", "RT2", "RT3"])
        left_layout.addWidget(self.GPCcalibtable)
        # Buttons
        self.load_btn = QPushButton("Load Calibration")
        self.clear_btn = QPushButton("Clear Calibration")
        self.save_btn = QPushButton("Save Calibration")
        self.fit_btn = QPushButton("Fit Calibration")
        self.plot_btn = QPushButton("Plot all chromatograms")
        self.connect_TC08_btn = QPushButton("Connect TC08")
        self.connect_TC08_btn.setStyleSheet("background-color: grey; color: white;")

        # Create groupbox for instrument control buttons
        self.instrument_control = QGroupBox("Instrument control")
        self.instrument_control.setContentsMargins(0, 0, 0, 0)        
        self.instrument_control_layout = QVBoxLayout()
        self.instrument_control_layout.addWidget(self.connect_TC08_btn)
        self.instrument_control.setLayout(self.instrument_control_layout)

        # Create groupbox for data handling buttons
        self.data_handling = QGroupBox("Data handling")
        # Add buttons to VBox and then groupbox
        btn_layout = QVBoxLayout()
        for btn in [self.load_btn, self.clear_btn, self.save_btn, self.fit_btn, self.plot_btn]:
            btn_layout.addWidget(btn)
        self.data_handling.setLayout(btn_layout)
        
        self.calibrant_injection = QGroupBox("Calibrant injection") 
        # Calibrant addition - MW, 
        self.mw_label = QLabel("MW")
        self.mw_input = QLineEdit()
        newcalibrant_layout = QGridLayout()
        newcalibrant_layout.addWidget(self.mw_label, 0, 0)
        newcalibrant_layout.addWidget(self.mw_input, 0, 1)
        self.overlay_checkbox = QCheckBox("Overlay Chromatograms?")
        newcalibrant_layout.addWidget(self.overlay_checkbox, 1, 0)
        self.add_calibrant_btn = QPushButton("Add new calibrant run")
        newcalibrant_layout.addWidget(self.add_calibrant_btn, 1, 1)
        # Start and End time
        self.start_label = QLabel("Start Time")
        self.start_time = QLabel("Start")
        self.end_label = QLabel("End Time")
        self.end_time = QLabel("End")
        newcalibrant_layout.addWidget(self.start_label, 2, 0)
        newcalibrant_layout.addWidget(self.end_label, 2, 1)
        newcalibrant_layout.addWidget(self.start_time, 3, 0)
        newcalibrant_layout.addWidget(self.end_time, 3, 1)
        self.calibrant_injection.setLayout(newcalibrant_layout)


        # Bring bottom left layout together for adding to left
        lb_layout = QHBoxLayout()
        lb_layout.addWidget(self.instrument_control)
        lb_layout.addWidget(self.data_handling)        
        lb_layout.addWidget(self.calibrant_injection)
        left_layout.addLayout(lb_layout)
        # Add the left layout to the main layout
        main_layout.addLayout(left_layout)
        # Right section for graphs
        right_layout = QVBoxLayout()
        # Live RI graph
        self.live_RI_signal = pg.PlotWidget(title="Live RI signal")
        self.live_RI_signal.enableAutoRange(axis='x', enable=True)
        self.live_RI_signal.enableAutoRange(axis='y', enable=True)
        self.curve = self.live_RI_signal.plot()
        # Chromatograms graph
        self.gpc_trace = pg.PlotWidget(title="Chromatograms")
        self.gpc_trace.setXRange(0, 230)
        # Calibration graph
        self.current_calib_plot = pg.PlotWidget(title="Current Calibration")
        self.current_calib_plot.setYRange(2.5, 6)
        self.current_calib_plot.setXRange(120, 230)
        # Bring right layour together
        right_layout.addWidget(self.live_RI_signal)
        right_layout.addWidget(self.gpc_trace)
        right_layout.addWidget(self.current_calib_plot)
        # Add the right layout to the main layout
        main_layout.addLayout(right_layout)
        # Set stretch factors for right and left
        main_layout.setStretch(0, 2)  # Left section gets less space
        main_layout.setStretch(1, 3)  
        self.GPC_calibrateBox.setLayout(main_layout)
        self.Layout.addWidget(self.GPC_calibrateBox)



############################## ASSIGN CALLBACKS TO BUTTONS ##############################
        self.load_btn.clicked.connect(self.load_cal_callback) 
        self.plot_btn.clicked.connect(self.plot_all_chroms)
        self.fit_btn.clicked.connect(self.fit_cal_callback)
        self.add_calibrant_btn.clicked.connect(self.add_calibrant_callback)
        self.connect_TC08_btn.clicked.connect(self.toggle_connection)
        self.save_btn.clicked.connect(self.save_cal_callback)
############################## CALLBACK FUNCTIONS ##############################


############################## Basic functions for data manipulation #########################
    def load_cal_callback(self):
        # Open a file dialog to select an Excel file
        options = QFileDialog.Options()
        cal_file, path = QFileDialog.getOpenFileName(self, "Load Calibration File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        
        if cal_file:
            fullname = f"{cal_file}"
            try:
                # Read the calibration data
                calibration_data = pd.read_excel(fullname, sheet_name='Calibration')
                chromatograms = pd.read_excel(fullname, sheet_name='Chromatograms')
                
                # Update the calibration table (assuming you have a table to display this)
                self.GPCcalibtable.setRowCount(len(calibration_data))
                for i in range(len(calibration_data)):
                    for j in range(calibration_data.shape[1]):
                        item = QTableWidgetItem(str(calibration_data.iat[i, j]))
                        self.GPCcalibtable.setItem(i, j, item)

                # Store chromatograms in instance variable
                self.chromatograms = chromatograms
                
                # Clear previous plots
                self.current_calib_plot.clear()
                
                # Plot the calibration data as a scatter
                self.current_calib_plot.plot(calibration_data.iloc[:, 0], calibration_data.iloc[:, 1], pen=None, symbol='o',symbolBrush='b')

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load the Excel calibration data: {e}")
        try: 
            with open('Calibration.pkl', 'rb') as f:
                self.calibrationfit = pickle.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the pickle calibration data: {e}")
    


    def plot_all_chroms(self):
        """Plots all chromatograms from self.chromatograms."""
        if self.chromatograms is None or self.chromatograms.empty:
            QMessageBox.warning(self, "Warning", "No chromatogram data available.")
            return

        self.gpc_trace.clear()  # Clear previous plots

        num_cols = self.chromatograms.shape[1]

        # Loop over chromatogram data in column pairs (time, intensity)
        for i in range(0, num_cols, 2):
            if i + 1 < num_cols:  # Ensure we have pairs
                x_data = self.chromatograms.iloc[:, i].dropna().values  # Time
                y_data = self.chromatograms.iloc[:, i + 1].dropna().values  # Intensity
                
                if len(x_data) > 0 and len(y_data) > 0:
                    # Color changes every 3 plots
                    color_index = (i // 2) // 3 % len(self.red_shades)
                    color = self.red_shades[color_index]

                    self.gpc_trace.plot(x_data, y_data, pen=pg.mkPen(color))        

    def clear_cal_callback(self):
        # Clear the calibration table
        self.GPCcalibtable.clear()
        self.GPCcalibtable.setHorizontalHeaderLabels(["Residence Time", "Log(MW)", "MW", "RT1", "RT2", "RT3"])

    def save_cal_callback(self):
        # Save calibration to Excel
        chromatograms = self.chromatograms
        data = self.tablewidget_to_dataframe(self.GPCcalibtable)
        options = QFileDialog.Options()
        save_file, path = QFileDialog.getSaveFileName(self, "Save Calibration", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if save_file:
            try:
                with pd.ExcelWriter(save_file) as writer:
                    data.to_excel(writer, sheet_name='Calibration', index=False)
                    chromatograms.to_excel(writer, sheet_name='Chromatograms', index=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save the calibration data: {e}")
        if self.calibrationfit is not None:
            directory = os.path.dirname(save_file)
            pkl_file = os.path.join(directory, "Calibration.pkl")
            try:
                with open(pkl_file, 'wb') as f:
                    pickle.dump(self.calibrationfit, f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save the calibration fit: {e}") 

    def fit_cal_callback(self):
        RT_data = []
        logMW_data = []

        for row in range(self.GPCcalibtable.rowCount()):
            item_rt = self.GPCcalibtable.item(row, 0)
            item_logmw = self.GPCcalibtable.item(row, 1)
            if item_rt and item_logmw:
                RT_data.append(float(item_rt.text()))
                logMW_data.append(float(item_logmw.text()))
   
        p = np.polyfit(RT_data, logMW_data, 3)
        self.current_calib_plot.plot(np.arange(50, 230), np.polyval(p, np.arange(50, 230)), pen='r')
        self.calibrationfit = p


############################### Instrument functions ###############################        
    def toggle_connection(self):
        if not self.TC08connected:
            # Simulate connecting to the instrument
            success = self.connect_TC08()
            print(success)
            if success:
                
                self.TC08connected = True
                self.connect_TC08_btn.setText("Connected to TC08")
                self.connect_TC08_btn.setStyleSheet("background-color: green; color: white;")
        else:
            self.disconnect_TC08()
            self.TC08connected = False
            self.connect_TC08_btn.setText("Connect TC08")
            self.connect_TC08_btn.setStyleSheet("background-color: grey; color: white;")    
    
    def connect_TC08(self):
        print("Connecting to TC08...")
        self.PicoGPC = PicoGPC.PicoGPC(self)
        self.TC08 = self.PicoGPC.connect()
        self.PicoGPC.rollingdataReady.connect(self.update_rolling_plot)
        return True
        
    def disconnect_TC08(self):
        print("Disconnecting from TC08...")
        self.PicoGPC.disconnect()
        self.PicoGPC.rollingdataReady.disconnect()
    
    def update_rolling_plot(self, data):
        if len(data) == 3:
            x, ri, _uv = data
        else:
            x, ri = data
        # set X range to show last 800 seconds of data, with slicing
        max_points = 800 * 5 # 5 points per second
        if len(x) > max_points:
            x = x[-max_points:]
            ri = ri[-max_points:]
        
        # self.live_RI_signal.clear()
        # self.live_RI_signal.plot(x, y, pen='g')
        # self.curve = self.live_RI_signal.plot()
        self.curve.setData(x, ri)

    def add_calibrant_callback(self):
        if self.TC08connected == False:
            QMessageBox.warning(self, "Warning", "TC08 is not connected.")
            return

        
        self.GPC = GPC_handler.GPC_handler(self, main=self.main, PicoGPC=self.PicoGPC)
        self.GPC.GPC_complete.connect(self.GPC_complete_callback)
        # print("Signal connected:", self.GPC.GPC_complete.isSignalConnected(self.GPC_complete_callback))   
        self.GPC.GPC_start(type='calibrant')
                # sampleValve = self.main.controller.valve5
        # sampleValve.writedelaytime("10")
        # sampleValve.ValveSample()

    def GPC_complete_callback(self, calibResults):
        print("Max Elution time in GUI:", calibResults["max_elution_time"])
        self.calibResults = calibResults
        chromatograms = calibResults["chrom"]
        chromatograms = pd.DataFrame(chromatograms, columns=['Time', 'Intensity'])
        RT = self.calibResults["max_elution_time"]
        # Plot the chromatogram
        if not self.overlay_checkbox.isChecked():
            self.gpc_trace.clear()
        self.gpc_trace.plot(chromatograms['Time'], chromatograms['Intensity'], pen='b')
        #Append chromatograms to self.chromatograms
        if hasattr(self, 'chromatograms'):
            self.chromatograms = pd.concat([self.chromatograms, chromatograms], axis=1)
        else:
            self.chromatograms = chromatograms
        self.update_calibration_table(RT, self.mw_input.text())
        # Plot Residence Time vs Log(MW) in current_calib_plot
        self.current_calib_plot.clear()
        #Extract data from table and convert to arrays for plotting
        RT_data = []
        logMW_data = []
        for row in range(self.GPCcalibtable.rowCount()):
            item_rt = self.GPCcalibtable.item(row, 0)
            item_logmw = self.GPCcalibtable.item(row, 1)
            if item_rt and item_logmw:
                RT_data.append(float(item_rt.text()))
                logMW_data.append(float(item_logmw.text()))

        self.current_calib_plot.plot(RT_data, logMW_data, pen=None, symbol='o', symbolBrush='b')
        
    def tablewidget_to_dataframe(self, table_widget):
        rows = table_widget.rowCount()
        columns = table_widget.columnCount()

        # Get headers
        header_labels = [table_widget.horizontalHeaderItem(col).text() if table_widget.horizontalHeaderItem(col) else f"Column {col}" for col in range(columns)]

        # Get cell data
        data = []
        for row in range(rows):
            row_data = []
            for col in range(columns):
                item = table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        # Create DataFrame
        return pd.DataFrame(data, columns=header_labels)
    
    def update_calibration_table(self, RT, mw_text):
        try:
            mw = float(mw_text)
        except ValueError:
            print("Invalid MW input.")
            return

        found = False

        # Loop through table rows to find matching MW
        for row in range(self.GPCcalibtable.rowCount()):
            item = self.GPCcalibtable.item(row, 2)  # MW column
            if item is None:
                continue
            try:
                mw_existing = float(item.text())
            except ValueError:
                continue

            if mw_existing == mw:
                found = True
                # Try to place RT in RT2 or RT3
                rt2_item = self.GPCcalibtable.item(row, 4)
                rt3_item = self.GPCcalibtable.item(row, 5)

                if rt2_item is None or rt2_item.text().strip() == "":
                    self.GPCcalibtable.setItem(row, 4, QTableWidgetItem(f"{RT:.4f}"))
                elif rt3_item is None or rt3_item.text().strip() == "":
                    self.GPCcalibtable.setItem(row, 5, QTableWidgetItem(f"{RT:.4f}"))
                else:
                    # All RTs filled — can't add more
                    print(f"MW {mw} already has 3 RTs recorded.")
                    return

                # Read RT1–RT3 for mean
                rt_values = []
                for col in [3, 4, 5]:
                    item = self.GPCcalibtable.item(row, col)
                    if item and item.text().strip():
                        try:
                            rt_values.append(float(item.text()))
                        except ValueError:
                            pass

                if rt_values:
                    rt_mean = np.mean(rt_values)
                    self.GPCcalibtable.setItem(row, 0, QTableWidgetItem(f"{rt_mean:.4f}"))  # Residence Time

                return  # We're done updating

        # If MW not found, add a new row
        if not found:
            new_row = self.GPCcalibtable.rowCount()
            self.GPCcalibtable.insertRow(new_row)

            # Add data: [Residence Time, log10(MW), MW, RT1, RT2, RT3]
            log_mw = np.log10(mw)
            data = [f"{RT:.4f}", f"{log_mw:.4f}", f"{mw:.4f}", f"{RT:.4f}", "", ""]
            for col, val in enumerate(data):
                self.GPCcalibtable.setItem(new_row, col, QTableWidgetItem(val))

