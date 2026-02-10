# PyQt5 preamble
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QLabel,
                             QCheckBox, QLineEdit, QGridLayout, QGroupBox, QFileDialog, QMessageBox, QInputDialog, QButtonGroup)
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



class GPC_runner(QtWidgets.QWidget):
    def __init__(self, parent, main):
############################## PREAMBLE ##############################
        super().__init__(parent)
        self.red_shades = [QColor(139, 0, 0, 255 - i * 25) for i in range(10)]  # Dark red (139,0,0) to lighter
        self.main = main
        self.TC08connected = False
        self.all_GPCResults = []
        # self.GPCValve = self.main.controller.valve5
        # Establish signal to a slot for GPC_handler to emit data to
        # self.gpc_handler = GPC_handler.GPC_handler(self, self, None)
        # self.gpc_handler.GPC_complete.connect(self.GPC_complete_callback)
        
############################## LAYOUT ##############################
        # Set the master layout of the GPC_Runner tab onto which all widgets are placed
        self.Layout = QtWidgets.QGridLayout()
        self.setLayout(self.Layout)
        # Main groupBox for all input and calculated experimental parameters
        self.GPC_runnerBox = QtWidgets.QGroupBox("GPC Analysis Runner")
        self.GPC_runnerBox.setMaximumSize(1800, 910)
        self.GPC_runnerBox.setContentsMargins(10, 5, 10, 5)
        main_layout = QHBoxLayout()

        # Left section for table and buttons
        left_layout = QVBoxLayout()
        # Table
        self.GPCResultstable = QTableWidget(0, 5)
        self.GPCResultstable.setHorizontalHeaderLabels(["Sample ID", "Start Time", "M_n", "M_w", "Dispersity"])
        left_layout.addWidget(self.GPCResultstable)
        # Buttons
        self.save_btn = QPushButton("Save GPC data")
        self.plot_btn = QPushButton("Plot all chromatograms")
        self.load_btn = QPushButton("Load GPC data")
        self.connect_TC08_btn = QPushButton("Connect TC08")
        self.connect_TC08_btn.setStyleSheet("background-color: grey; color: white;")
        self.single_inj = QPushButton("Single injection")
        self.triple_inj = QPushButton("Triple injection")
        self.stop_btn = QPushButton("Stop measurement")
        self.stop_btn.setStyleSheet("background-color: red; color: white;")


        self.single_inj.setCheckable(True)
        self.triple_inj.setCheckable(True)

        self.injbuttongroup = QButtonGroup()
        self.injbuttongroup.setExclusive(True)
        self.injbuttongroup.addButton(self.single_inj)
        self.injbuttongroup.addButton(self.triple_inj)
        self.single_inj.setChecked(True)
        # Set styles
        self.update_button_styles()

        # Create groupbox for instrument control buttons
        self.instrument_control = QGroupBox("Instrument control")
        self.instrument_control.setContentsMargins(0, 0, 0, 0)
        
        # Add buttons to VBox and then groupbox
        btn_layout1 = QVBoxLayout()
        for btn in [self.connect_TC08_btn, self.single_inj, self.triple_inj, self.stop_btn]:
            btn_layout1.addWidget(btn)
        self.instrument_control.setLayout(btn_layout1)
        
        # Create groupbox for data handling buttons
        self.data_handling = QGroupBox("Data handling")
        # Add buttons to VBox and then groupbox
        btn_layout2 = QVBoxLayout()
        for btn in [self.save_btn, self.plot_btn, self.load_btn]:
            btn_layout2.addWidget(btn)
        self.data_handling.setLayout(btn_layout2)
        # Calibrant addition - MW, 
        # Create groupbox for new sample addition
        self.new_analysis = QGroupBox("New analysis")
        self.sampleID_label = QLabel("Sample ID")
        self.sampleID_input = QLineEdit()
        newanalysis_layout = QGridLayout()
        newanalysis_layout.addWidget(self.sampleID_label, 0, 0)
        newanalysis_layout.addWidget(self.sampleID_input, 0, 1)
        self.overlay_checkbox = QCheckBox("Overlay Chromatograms?")
        newanalysis_layout.addWidget(self.overlay_checkbox, 1, 0)
        self.inject_sample_btn = QPushButton("Inject sample")
        newanalysis_layout.addWidget(self.inject_sample_btn, 1, 1)
        # Start and End time
        self.start_label = QLabel("Start Time")
        self.start_time = QLabel("Start")
        self.end_label = QLabel("End Time")
        self.end_time = QLabel("End")
        newanalysis_layout.addWidget(self.start_label, 2, 0)
        newanalysis_layout.addWidget(self.end_label, 2, 1)
        newanalysis_layout.addWidget(self.start_time, 3, 0)
        newanalysis_layout.addWidget(self.end_time, 3, 1)

        # Add newanalysis_layout to New analysis groupbox
        self.new_analysis.setLayout(newanalysis_layout)

        # Bring bottom left layout together for adding to left
        lb_layout = QHBoxLayout()
        lb_layout.addWidget(self.instrument_control)
        lb_layout.addWidget(self.data_handling)        
        lb_layout.addWidget(self.new_analysis)
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
        # Live UV graph
        self.live_UV_signal = pg.PlotWidget(title="Live UV signal")
        self.live_UV_signal.enableAutoRange(axis='x', enable=True)
        self.live_UV_signal.enableAutoRange(axis='y', enable=True)
        self.uv_curve = self.live_UV_signal.plot()
        # Chromatograms graph
        self.gpc_trace = pg.PlotWidget(title="Chromatograms")
        self.gpc_trace.setXRange(0, 220)
        # Calibration graph
        self.MW_slice_plot = pg.PlotWidget(title="MW slice")
        self.MW_slice_plot.setXRange(120, 220)
        # Bring right layout together
        right_layout.addWidget(self.live_RI_signal)
        right_layout.addWidget(self.live_UV_signal)
        right_layout.addWidget(self.gpc_trace)
        right_layout.addWidget(self.MW_slice_plot)
        # Add the right layout to the main layout
        main_layout.addLayout(right_layout)
        # Set stretch factors for right and left
        main_layout.setStretch(0, 2)  # Left section gets less space
        main_layout.setStretch(1, 3)  
        self.GPC_runnerBox.setLayout(main_layout)
        self.Layout.addWidget(self.GPC_runnerBox)



############################## ASSIGN CALLBACKS TO BUTTONS ##############################
        self.plot_btn.clicked.connect(self.plot_all_chroms)
        self.inject_sample_btn.clicked.connect(self.inject_sample_callback)
        self.connect_TC08_btn.clicked.connect(self.toggle_connection)
        self.save_btn.clicked.connect(self.save_GPCdata_callback)
        self.load_btn.clicked.connect(self.load_GPCdata_callback)
        self.injbuttongroup.buttonClicked.connect(self.update_button_styles)
        self.stop_btn.clicked.connect(self.stop_measurement_callback)


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
            x, ri, uv = data
        else:
            x, ri = data
            uv = None
        # set X range to show last 800 seconds of data, with slicing
        max_points = 800 * 5 # 5 points per second
        if len(x) > max_points:
            x = x[-max_points:]
            ri = ri[-max_points:]
            if uv is not None:
                uv = uv[-max_points:]
        
        # self.live_RI_signal.clear()
        # self.live_RI_signal.plot(x, y, pen='g')
        # self.curve = self.live_RI_signal.plot()
        self.curve.setData(x, ri)
        if uv is not None:
            self.uv_curve.setData(x, uv)

    def inject_sample_callback(self):
        if self.TC08connected == False:
            QMessageBox.warning(self, "Warning", "TC08 is not connected.")
            return
        
        self.GPC = GPC_handler.GPC_handler(self, main=self.main, PicoGPC=self.PicoGPC)
        self.GPC.GPC_complete.connect(self.GPC_complete_callback)
        # print("Signal connected:", self.GPC.GPC_complete.isSignalConnected(self.GPC_complete_callback))   
        if self.single_inj.isChecked():
            self.GPC.GPC_start(type='default', injnum=1, sampleID=self.sampleID_input.text())
        elif self.triple_inj.isChecked():
            self.GPC.GPC_start(type='default', injnum=3, sampleID=self.sampleID_input.text())
                # sampleValve = self.main.controller.valve5
        # sampleValve.writedelaytime("10")
        # sampleValve.ValveSample()


    def GPC_complete_callback(self, GPCResults):
            
            self.GPCResults = GPCResults
            injnum = self.GPCResults["injnum"]
            chromatograms = GPCResults["chrom"]
            polpeak = GPCResults["polpeak"]
            if not self.overlay_checkbox.isChecked():
                self.gpc_trace.clear()
                self.MW_slice_plot.clear()            

            for i in range(injnum):
                # Plotting chromatograms and polpeak data
                if not self.GPCResults["Averages"]["MP"].values[0] == 0:
                    polpeak_temp = polpeak.iloc[:, 2*i:2*i+2]
                    polpeak_temp.columns=['MW', 'Intensity']
                    self.MW_slice_plot.plot(polpeak_temp['MW'], polpeak_temp['Intensity'])
                chromatograms_temp = chromatograms.iloc[:,2*i:2*i+2]
                chromatograms_temp.columns=['Time', 'Intensity']
                self.gpc_trace.plot(chromatograms_temp['Time'], chromatograms_temp['Intensity'], pen='b')
            #Pull average data from GPCResults and add to table 
            # structure is Results["Averages"] = pd.DataFrame([[np.mean(Results["Mn"]), np.mean(Results["Mw"]), np.mean(Results["PD"]), np.mean(Results["MP"])]], columns=["Mn", "Mw", "PD", "MP"])
            sampleID = self.GPCResults["sampleID"]
            StartTime = self.GPCResults["StartTime"][0].strftime("%Y-%m-%d %H:%M:%S")
            Mn = self.GPCResults["Averages"]["Mn"].values[0]
            Mw = self.GPCResults["Averages"]["Mw"].values[0]
            PD = self.GPCResults["Averages"]["PD"].values[0]
            values = [sampleID, StartTime, Mn, Mw, PD]
            # Add these values to the table
            row_position = self.GPCResultstable.rowCount()
            self.GPCResultstable.insertRow(row_position)
            for i, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.GPCResultstable.setItem(row_position, i, item)
            
            self.all_GPCResults.append(self.GPCResults)
            #Append chromatograms to self.chromatograms
            if hasattr(self, 'rawchrom'):
                self.rawchrom = pd.concat([self.rawchrom, self.GPCResults["rawchrom"]], axis=1)
            else:
                self.rawchrom = self.GPCResults["rawchrom"]
            
            
    def stop_measurement_callback(self):
        # Stop the measurement
        if hasattr(self, 'PicoGPC'):
            self.PicoGPC.stopMeasure()
            self.PicoGPC.disconnect()
            self.PicoGPC.rollingdataReady.disconnect()
            self.TC08connected = False
            self.connect_TC08_btn.setText("Connect TC08")
            self.connect_TC08_btn.setStyleSheet("background-color: grey; color: white;")
        else:
            QMessageBox.warning(self, "Warning", "No measurement in progress.")
        # Check if GPC_handler still has running APScheduler and a running job, GPC_inject
        if hasattr(self, 'GPC') and hasattr(self.GPC, 'GPCscheduler'):
            if self.GPC.GPCscheduler.running:
                self.GPC.GPCscheduler.remove_job('GPC_inject')
                self.GPC.GPCscheduler.shutdown(wait=False)
                self.GPC.GPCscheduler = None
                self.GPC = None

                    


    def save_GPCdata_callback(self):
        # Save calibration to Excel
        rawchrom = self.rawchrom
        data = self.tablewidget_to_dataframe(self.GPCResultstable)

        options = QFileDialog.Options()
        save_file, path = QFileDialog.getSaveFileName(self, "Save GPC Data", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if save_file:
            try:
                with pd.ExcelWriter(save_file) as writer:
                    data.to_excel(writer, sheet_name='GPC data', index=False)
                    rawchrom.to_excel(writer, sheet_name='rawChromatograms', index=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save the GPC data in Excel: {e}")
            directory = os.path.dirname(save_file)
            dt=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            pkl_file = os.path.join(directory, f"GPCresults_{dt}.pkl")
            try:
                with open(pkl_file, 'wb') as f:
                    pickle.dump(self.all_GPCResults, f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save the GPC Results in pickle: {e}")

    def load_GPCdata_callback(self):
        # Load data from GPCresults pickle file
        options = QFileDialog.Options()
        load_file, path = QFileDialog.getOpenFileName(self, "Load GPC Data", "", "Pickle Files (*.pkl);;All Files (*)", options=options)
        if load_file:
            try:
                with open(load_file, 'rb') as f:
                    self.all_GPCResults = pickle.load(f)
                    
                # Load chromatograms and rawchrom from self.all_GPCResults
                self.chromatograms = pd.DataFrame()
                self.rawchrom = pd.DataFrame()
                for result in self.all_GPCResults:
                    chromatograms = result["chrom"]
                    self.chromatograms = pd.concat([self.chromatograms, chromatograms], axis=1)
                    rawchrom = result["rawchrom"]
                    self.rawchrom = pd.concat([self.rawchrom, rawchrom], axis=1)


                # Clear the table before loading new data
                self.GPCResultstable.setRowCount(0)

                # Populate the table with loaded data
                for result in self.all_GPCResults:
                    sampleID = result["sampleID"]
                    StartTime = result["StartTime"][0].strftime("%Y-%m-%d %H:%M:%S")
                    Mn = result["Averages"]["Mn"].values[0]
                    Mw = result["Averages"]["Mw"].values[0]
                    PD = result["Averages"]["PD"].values[0]
                    values = [sampleID, StartTime, Mn, Mw, PD]

                    row_position = self.GPCResultstable.rowCount()
                    self.GPCResultstable.insertRow(row_position)
                    for i, value in enumerate(values):
                        item = QTableWidgetItem(str(value))
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                        self.GPCResultstable.setItem(row_position, i, item)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load the GPC data: {e}")




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
    
    def update_button_styles(self):
        # Style for the checked button
        checked_style = """
            QPushButton:checked {
                background-color: blue;
                color: white;
                border: blue;
                padding: 10px;
            }
        """
        # Style for the unchecked button
        unchecked_style = """
            QPushButton {
                background-color: grey;
                color: white;
                border: white;
                padding: 10px;
            }
        """
        # Apply styles
        self.single_inj.setStyleSheet(checked_style if self.single_inj.isChecked() else unchecked_style)
        self.triple_inj.setStyleSheet(checked_style if self.triple_inj.isChecked() else unchecked_style)