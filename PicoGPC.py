from tc08usb import TC08USB, USBTC08_ERROR, USBTC08_UNITS, USBTC08_TC_TYPE
from PyQt5 import QtWidgets, QtCore 
import pyqtgraph as pg
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import numpy as np
import threading
import datetime
import time
import pandas as pd

class PicoGPC(QObject):
    dataReady = pyqtSignal(pd.DataFrame)
    rollingdataReady = pyqtSignal(object)
    def __init__(self, parent, ):
        super().__init__(parent)
        


    def connect(self):
        self.tc08usb = TC08USB()
        self.tc08usb.open_unit()
        self.tc08usb.set_mains(50)
        self.channels = [1, 2]
        self.numChannels = len(self.channels)
        for i in self.channels:
            self.tc08usb.set_channel(i, USBTC08_TC_TYPE.X)
        self.tc08usbConnected = True
        print('TC-08 picologger connected')
        return self.tc08usbConnected

    def measure(self, run_time): # Opens new thread for RI_Signal measurement  
        self.run_time = run_time
        print("runtime", self.run_time)
        self.timer = threading.Timer(self.run_time, self.delayed_return)
        self.timer.start() # Start the timer
        if self.tc08usbConnected:
            self.tc08usbRun = True
            self.readRI_SignalThread = threading.Thread(target = self.read_data)
            self.readRI_SignalThread.start()
            self.stopRI_SignalThread = False

    def read_data(self):
        self.RI_SignalData = np.array([])
        self.timeAxis = np.array([])
        self.channel1 = np.array([]) #initialise data array for voltage
        self.channel2 = np.array([]) #same for second channel (e.g. UV)
        self.timeAxis = np.array([])
        self.startMeasurementTime = datetime.datetime.now()

        while self.tc08usbRun:
            self.tc08usb.get_single()
            self.experimentTime = (datetime.datetime.now() - self.startMeasurementTime).total_seconds()
            self.timeAxis = np.append(self.timeAxis, self.experimentTime)
            newData = np.array([self.tc08usb[1], self.tc08usb[2]]) # gathers new RI/UV values from TC-08
            self.channel1 = np.append(self.channel1, newData[0]) # appends new data for each channel to the old array
            self.channel2 = np.append(self.channel2, newData[1])
            # self.channel1Value.setText(f"{newData[0]:.6f}")
            # self.RI_SignalXRange = np.size(self.channel1)*1.2
            # self.RI_SignalYRange = max(self.channel1)*1.2
            # self.dataFeed.setXRange(0, self.RI_SignalXRange + 100, padding = 0)
            # self.dataFeed.setYRange(0, self.RI_SignalYRange + 20, padding = 0)
            self.rollingdataReady.emit((self.timeAxis, self.channel1, self.channel2))
            
            time.sleep(0.2)
            
            if self.stopRI_SignalThread:
                break


    def delayed_return(self):
        print(self.timeAxis)
        print(self.channel1)

        GPCdata = pd.DataFrame(data=[self.timeAxis, self.channel1, self.channel2]).T
        GPCdata.columns=["Time", "RI", "UV"]
        self.dataReady.emit(GPCdata)
        self.stopMeasure()
        self.timer.cancel()

    def stopMeasure(self):
        self.stopRI_SignalThread = True
        if hasattr(self, 'readRI_SignalThread') and self.readRI_SignalThread.is_alive():
            self.readRI_SignalThread.join()
        if hasattr(self, 'timer') and self.timer.is_alive():
            self.timer.cancel()

        self.tc08usbRun = False
        print("Measurement stopped")


    
    def saveData(self):
        savePath = r"G:\My Drive\Coding\P3_SDL" + "\-GPC.csv"
        print(savePath)
        df = pd.DataFrame(data=[self.x, self.channel1]).T
        df.columns=['Time (s)',
        'Channel 1 Voltage'
        ]        
        pd.DataFrame(df).to_csv(savePath)

    def disconnect(self):
        self.tc08usb.close_unit()
        print("disconnected from TC08")