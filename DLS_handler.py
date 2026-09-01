from PyQt5 import QtWidgets
import numpy as np
import pyqtgraph as pg
import threading
import pandas as pd
import time
from datetime import datetime
import glob
import os

class StoppedFlowDLS(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(StoppedFlowDLS, self).__init__(parent)

        self.main = main
        self.DLSPump = self.main.controller.pump10
        self.DLSValve = self.main.controller.valve4

        DLSGroupBox = QtWidgets.QGroupBox("Particle size analysis")
        DLSGroupBox.setFixedSize(600, 250)

        self.sampleNameText = QtWidgets.QLineEdit("Sample name")
        self.sampleNameText.setFixedSize(75, 25)

        self.manualMeasurementBtn = QtWidgets.QPushButton("Measure")
        self.manualMeasurementBtn.setFixedSize(75, 25)
        self.manualMeasurementBtn.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")

        self.startPumpBtn = QtWidgets.QPushButton("Run pump")
        self.startPumpBtn.setFixedSize(75, 25)
        self.startPumpBtn.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")

        self.stopPumpBtn = QtWidgets.QPushButton("Stop pump")
        self.stopPumpBtn.setFixedSize(75, 25)
        self.stopPumpBtn.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")

        self.switchValveBtn = QtWidgets.QPushButton("Switch valve")
        self.switchValveBtn.setFixedSize(75, 25)
        self.switchValveBtn.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")

        self.manualMeasurementBtn.clicked.connect(lambda: self.startScan(self.sampleNameText.text()))

        self.dataFeed = pg.PlotWidget()
        self.dataFeed.setBackground('#F4F4F4')
        self.dataFeed.setTitle("Intensity distribution", color='#000000')
        styles = {'color': '#000000', 'font-size': '14px'}
        self.dataFeed.setLabel('left', 'Normalised intensity', **styles)
        self.dataFeed.setLabel('bottom', 'Particle size [nm]', **styles)
        sizeData = np.array([])
        timeAxis = np.array([])
        self.data_line = self.dataFeed.plot(timeAxis, sizeData, pen='r')

        self._layout = QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        grid = QtWidgets.QGridLayout()
        innergrid10 = QtWidgets.QGridLayout()
        grid.addLayout(innergrid10, 1, 0)
        self._layout.addWidget(DLSGroupBox)
        DLSGroupBox.setLayout(grid)
        innergrid10.addWidget(self.sampleNameText, 0, 0)
        innergrid10.addWidget(self.manualMeasurementBtn, 1, 0)
        innergrid10.addWidget(self.startPumpBtn, 2, 0)
        innergrid10.addWidget(self.stopPumpBtn, 3, 0)
        innergrid10.addWidget(self.switchValveBtn, 4, 0)
        grid.addWidget(self.dataFeed, 1, 1)
        grid.setContentsMargins(3, 3, 3, 3)

        self.DLSfindPath = r'C:\Users\Pcubed\Documents\Peter\Online-DLS\Data-hold'
        self.DLSsavePath = r'C:\Users\Pcubed\Documents\Peter\Online-DLS\Data-save'

        self.scanning = 0
        self.DLSDataCollected = 0
        self.sampleList = []
        self.sizeList = []
        self.dataDict = {}
    
### Function for diverting and diluting a product sample to the DLS
    def sampleAndScan(self, concentration, flowRate, sampleID):
        print("Sampling for DLS measurement...")
        DLSconcentration = 0.01 # desired concentration for taking the DLS measurement (1 %w/w on the basis that going much lower will require >10mL/min dilution)
        DLSdeadVolume = 2 # dead volume between DLS mixing point and end of flow cell in mL
        self.DLSflowRate = flowRate*((concentration/DLSconcentration) - 1) # calculated DLSpump flow rate for target DLS concentration
        polymerReplacementVolume = 0.5 # Volume to flow through product before starting DLS dilution to replace leftover polymer from last sample

        # DLSPump max flowrate = 10, setting a rate higher than this just sets it to 10, so if DLSflowRate > 10, return the actual DLSconcentration achieved
        if self.DLSflowRate > 10:
            self.DLSflowRate = 10
            DLSconcentration = concentration*flowRate/self.DLSflowRate
        self.DLSPump.setFlowrateText.setText(str(1))
        self.DLSPump.setFlowrate()

        self.DLSPump.start()
        print("Priming DLS tube")
        startPrimeDLStime = datetime.now()
        while not self.main.methodHandler.stopThread and (datetime.now() - startPrimeDLStime).seconds < 10:
            time.sleep(1)

        self.DLSValve.valveSwitch(position="B")  # this valve doesn't actually take a 'position' it just alternates the position it is at
        print("Switching to collect sample")

        # Calculate time to replace dead volume before water dilution
        DLSdilutionWaitTime = 60*polymerReplacementVolume/flowRate
        print(f'Replacing polymer before diluting for {DLSdilutionWaitTime / 60:.1f} min(s)...')
        DLSsamplingTimeStart = datetime.now()
        while not self.main.methodHandler.stopThread and (datetime.now() - DLSsamplingTimeStart).seconds < DLSdilutionWaitTime:
            time.sleep(1)

        self.DLSPump.setFlowrateText.setText(str(self.DLSflowRate))
        self.DLSPump.setFlowrate()

        # Calculate time (s) required to wash out and fill DLS flow cell
        DLSsteadyStateTime = 3.5*DLSdeadVolume/(self.DLSflowRate + flowRate)

        # Get sample to the DLS flow cell
        print(f'Diluting to steady-state for {DLSsteadyStateTime:.1f} min(s)')
        DLSsamplingTimeStart = datetime.now()
        while not self.main.methodHandler.stopThread and (datetime.now() - DLSsamplingTimeStart).seconds < 60*DLSsteadyStateTime:
            time.sleep(1)

        # Stop DLS pump and redirect flow to sampling system
        self.DLSPump.stop()
        self.DLSValve.valveSwitch(position="A") # this valve doesn't actually take a 'position' it just alternates the position it is at

        print('Starting DLS scan')
        self.sampleID = sampleID
        self.DLSstopThread = False
        if self.scanning == 0:
            self.DLSthread = threading.Thread(target=self.runScan)
            self.DLSthread.start()
        else:
            print("DLS measurement already in progress")
        return

    def runScan(self):
        self.scanning = 1
        DLSholdTimeStart = datetime.now()
        print(f'Holding sample in DLS cell whilst new measurement is completed')
        while not self.main.methodHandler.stopThread and (datetime.now() - DLSholdTimeStart).seconds < 180:
            time.sleep(1)
        self.startScanTime = datetime.now()
        self.DLSDataCollected = 0
        while not self.DLSstopThread and self.DLSDataCollected == 0 and (datetime.now() - self.startScanTime).seconds < 300:
            self.getData()
            time.sleep(1)
        self.scanning = 0
        return

    def getData(self):
        ### Pull data from the current .csv in the target folder where the DLS is designated to save to
        print("waiting for data...")

        # Look in data holding folder and get the timestamp that it was uploaded
        for file in glob.glob(self.DLSfindPath + r"\*.csv"):
            data = pd.read_csv(file, header=None)
            fileStatInfo = os.stat(file)
            fileCreateTime = datetime.fromtimestamp(fileStatInfo.st_mtime)

        ### Check the current .csv file was created in the last 2 mins, and if so backup into the storage folder including current sample name
        if (self.startScanTime - fileCreateTime).seconds < 120:
            self.zAve = data.iloc[0, 0]
            self.PDI = data.iloc[0, 1]
            self.countRate = data.iloc[0, 2]
            self.particleSize = list(data.iloc[0, 3:73])
            self.intensityDist = list(data.iloc[0, 74:144])
            self.volumeDist = list(data.iloc[0, 145:215])
            self.numberDist = list(data.iloc[0, 216:286])
            
            summaryData = {
                "Sample ID": [self.sampleID],
                "Z-Average particle size (nm)": [self.zAve],
                "PDI": [self.PDI],
                "Count-rate": [self.countRate]
            }
            print(f'SummaryData = {summaryData}')
            summaryDF = pd.DataFrame.from_dict(summaryData)
            summaryDF.to_csv(self.DLSsavePath + r"/" + str(self.sampleID) + "-summary.csv")
            distributionsData = {
                "Particle size (nm)": self.particleSize,
                "Intensity": self.intensityDist,
                "Volume": self.volumeDist,
                "Number": self.numberDist
            }
            distributionsDF = pd.DataFrame(distributionsData)
            distributionsDF.to_csv(self.DLSsavePath + r"/" + str(self.sampleID) + "-distributions.csv")
            sizeDistDF = pd.DataFrame([self.particleSize, self.intensityDist, self.volumeDist, self.numberDist]).T
            sizeDistDF.columns = ["Particle size (nm)", "Intensity average", "Volume average", "Number average"]

            self.DLSDataCollected = 1
            self.DLSstopThread = True
            print(f"DLS data saved for {str(self.sampleID)}")

        else:
            print("No measurement file created in the last 2 minutes")

        self.DLSPump.start()
        DLSflushTimeStart = datetime.now()
        print('Flushing DLS')
        while not self.main.methodHandler.stopThread and (datetime.now() - DLSflushTimeStart).seconds < 10:
            time.sleep(1)
        self.DLSPump.stop()
        return