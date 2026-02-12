from ast import Return
from pickle import FALSE
import typing
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtWidgets import QWidget
import pyqtgraph as pg
import sys
import numpy as np
import pandas as pd,os
from PyQt5.QtCore import pyqtSlot, QTimer
import pumpWidget as pw
import datetime
import time
import thermocontroller_driver
from thermocontroller_driver import Furnace
import signal


class mainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(mainWindow, self).__init__()
        global windowRun
        windowRun = False
        self.centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralWidget)

        self._active_step_id = 0
        
        # self.tab_main = QtWidgets.QTabWidget(self)
        # self.tab_main.layout = QtWidgets.QGridLayout()
        # self.tab_main.setStyleSheet("QTabBar::tab { height: 30px; width: 150px }")
        self.layout = QtWidgets.QGridLayout(self.centralWidget)

        self.start_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # string start time for log filename
        self.start_time_int = datetime.datetime.now() # datetime object for reaction time calculations
        self._csv_initialized = False

        self.logging_interval = 20 * 1000 #every 20 seconds in ms (starts when the script is run)
        self.temp_logger = QTimer()
        self.temp_logger.timeout.connect(self.continuous_log_function)
        self.temp_logger.start(self.logging_interval)

        self.pumpsBox = QtWidgets.QGroupBox("Pumps")
        self.pumpsBox.setMaximumHeight(400)
        self.pumpsBox.setMaximumWidth(1000)
        self.pumpsBox.setHidden(False)
        self.pumpsLayout = QtWidgets.QGridLayout(self.pumpsBox)
        self.layout.addWidget(self.pumpsBox)

        self.pump1 = pw.PumpControl(self, pumpName="Pump A")
        self.pump1.pumpModelCombo.setCurrentText("MilliGAT LF")
        self.pump1.formatWidget(pump="MilliGAT LF")
        self.pumpsLayout.addWidget(self.pump1, 0, 0, QtCore.Qt.AlignLeft)
        
        self.pump2 = pw.PumpControl(self, pumpName="Pump B")
        self.pump2.pumpModelCombo.setCurrentText("MilliGAT LF")
        self.pump2.formatWidget(pump="MilliGAT LF")
        self.pumpsLayout.addWidget(self.pump2, 0, 1, QtCore.Qt.AlignLeft)
        self.pumps = [self.pump1, self.pump2]

        self.pumpALLButton = QtWidgets.QPushButton("RUN ALL")
        self.pumpALLButton.setFixedSize(50, 25)
        self.pumpALLButton.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")
        self.pumpALLButton.clicked.connect(self.pump_ALL)
        self.pumpsLayout.addWidget(self.pumpALLButton,0, 2, QtCore.Qt.AlignLeft)
        
        self.runSequenceButton = QtWidgets.QPushButton("Run Sequence")
        self.runSequenceButton.setFixedSize(150, 30)
        self.runSequenceButton.clicked.connect(self.load_sequence) ##starts load sequence
        self.pumpsLayout.addWidget(self.runSequenceButton, 1, 0, QtCore.Qt.AlignLeft)
        
        self._sequence_cancelled = False
        self.thermo = Furnace() # create thermocontroller instance 
        self.a = 10  # Eurotherm correction factor
        self.tolerance = 0.1  # °C
        self.stability_time = 30  # seconds temperature must stay within tolerance
        self._temp_hold_start = None  
        
        self.stopSequenceButton = QtWidgets.QPushButton("Stop Sequence")
        self.stopSequenceButton.setFixedSize(150, 30)
        self.stopSequenceButton.clicked.connect(self.handle_stop_sequence)
        self.pumpsLayout.addWidget(self.stopSequenceButton, 1, 1, QtCore.Qt.AlignLeft)

    def pump_ALL(self):
        for pump in self.pumps:
            value = 1
            self.setFlowrates(pump)
        print("pump ALL", str(datetime.datetime.now()))
        self.continuous_log_function(event="Pump ALL")

    
    def setFlowrates(self, pump):
        flowRate = pump.setFlowrateText.text()
        print("fR=",flowRate)
        # pumpModel = pump.pumpModelCombo.currentText()
        # print(pumpModel)
        pump.setFlowrate()
        # try:
        #     if pumpModel == 'MilliGAT HF':
        #         pump.set_flow_rate(float(flowRate), pump_type='HF')
        #     elif pumpModel == "MilliGAT LF":
        #         pump.set_flow_rate(float(flowRate), pump_type="LF")
        #     elif pumpModel == 'Chemyx Fusion 6000X':
        #         pump.setRate(rate=flowRate, x=0)
        # except:
        #     print('No pump connected')
 

    def load_sequence(self):
        self.pump1.setFlowrateText.setText("0.5") #set flowrates to 1 to load reactor with material
        self.pump1.setFlowrate()
        self.pump2.setFlowrateText.setText("0.5")
        self.pump2.setFlowrate()

        print("Loading Reactor...")

        self.thermo.setpoint_1(20*self.a) # set initial temperature to 20 degrees C)

        self.continuous_log_function(event="Reactor Loading")

        QtCore.QTimer.singleShot(
            180000, 
            lambda: (
                self.continuous_log_function(event="Reactor Loaded"),
                self.T0_sequence(),
                self.continuous_log_function(event="T0 Started")
            )
         ) #waits 3 minutes before triggering the T0 Sequence next step
        

    def T0_sequence(self):
        self.pump1.setFlowrateText.setText("0.05") #set flowrates to 0.05 to run T0 (accumulated = 0.1 ml min)
        self.pump1.setFlowrate()
        self.pump2.setFlowrateText.setText("0.05")
        self.pump2.setFlowrate()

        self.thermo.setpoint_1(self.safe_read_temp()) #set temeprature to current temperature to hold steady during T0 

        self.continuous_log_function(event="Starting T0") #trigger log event

        QtCore.QTimer.singleShot(
            300000, #wait 5 minutes for T0 to complete, This will be marked in the log with Starting T0 and T0 Ended events
            lambda: (
                self.continuous_log_function(event="T0 Ended"),
                self.handle_run_sequence() # triggers run sequence after T0
            )
         )


    def safe_read_temp(self): # temperature read with retries - otherwise may throw error and stop program
        for attempt in range(3):
            try:
                return self.thermo.indicated() / self.a # read temperature and apply correction factor
            except Exception as e: 
               print(f"[Warning] Modbus read failed (attempt {attempt+1}/3): {e}") #log warning 
               time.sleep(1) # wait before retrying
        print("[Error] Failed to read temperature after 3 attempts — returning NaN.")
        return float('nan')
   

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("Pump Controller")
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
    
    

    def continuous_log_function(self,event=None): #logging function that runs every x seconds (set by self.logging_interval)
        log_dir = "Experimental_Logs"
        log_path = os.path.join(log_dir, f"experimental_log {self.start_time_str}.csv") #log path with start time in filename

        temp = self.safe_read_temp()
        now = datetime.datetime.now()

        reaction_time = None

        if hasattr(self, "start_time_int"):
            reaction_time = str(datetime.timedelta(seconds=int((now - self.start_time_int).total_seconds())))


        pump1_correction_factor_x_value = 1.0039  # adjust if pump 1 has different calibration

        pump2_correction_factor_x_value = 0.8948   # adjust if pump 2 has different calibration
        

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df_entry = pd.DataFrame([{
            "Time": timestamp,
            "Reaction Time": reaction_time,
            "Temperature": temp,
            "Step": getattr(self,"_sequence_index",None),
            "Flow_A": (float(self.pump1.setFlowrateText.text())*pump1_correction_factor_x_value), # retrieves the text from the flowrate input box and applies correction factor
            "Flow_B": (float(self.pump2.setFlowrateText.text())*pump2_correction_factor_x_value), # retrieves the text from the flowrate input box and applies correction factor
            "Event": event
        }])

        if not self._csv_initialized:
            df_entry.to_csv(log_path, index=False, mode='w')
            self._csv_initialized = True
        else:
            df_entry.to_csv(log_path, index=False, mode='a', header=False)
        
        with open(log_path, "a") as f:
            f.flush()
            os.fsync(f.fileno())

                

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("Pump Controller", "Pump Controller"))

    
    def handle_run_sequence(self):
        self.thermo.setpoint_1(20*self.a) # initial setpoint before sequence starts (20 degrees C)
        # Load CSV and verify columns   
        csv_path = os.path.join(os.path.dirname(__file__), "kinetics_sweep.csv")
        df = pd.read_csv(csv_path)
        required_cols = ['x_temperature', 'flow_rate_a', 'flow_rate_b', 'y_res_time','steady_state_delay']
        if not all(col in df.columns for col in required_cols):
            print(f"[Error] CSV file must contain columns: {required_cols}")
            return

        # Build a DataFrame with flow_rate_a and steady_state_delay calculated from y_res_time (in minutes)
        seq_df = pd.DataFrame({ #sequence dataframe
            'temperature': df['x_temperature'],
            'flow_rate_a': df['flow_rate_a'],
            'flow_rate_b': df['flow_rate_b'],
            'steady_state_delay': df['steady_state_delay'] # delay calculated from residence time (assumed minutes)
        })

        self.run_sequence_qt(seq_df)
        

    def run_sequence_qt(self, sequence_df): # separation of concerns - run_sequence_qt can be called from other functions 
        self._sequence_steps = sequence_df.to_dict('records')
        self._sequence_index = 0
        self._sequence_cancelled = False
        self.start_time = datetime.datetime.now() 
        self._run_next_step()
        

    def handle_stop_sequence(self):
        self._sequence_cancelled = True
        self.pump1.setFlowrateText.setText("0")
        self.pump1.setFlowrate()
        self.pump2.setFlowrateText.setText("0")
        self.pump2.setFlowrate()
        print("Sequence stopped, pumps set to zero.")

        self.continuous_log_function(event = "Sequence Stopped by user")



    def sample_initialization(self,flow_a,flow_b,_active_step_id):
        # in place of actual sample instruction  - will be dispenser control send commands
        sample_time = datetime.datetime.now()
        ## move to position x

        # console message
        print(f"Sample taken at {sample_time} | Step ID: {_active_step_id} | Flow A: {flow_a} | Flow B: {flow_b}")
        # add event to log
        self.continuous_log_function(event="Sample Taken")

        ## move to waste 

        

    def _on_sample_complete(self, _active_step_id, flow_a, flow_b):
        # call sample message then continue to next step
        # run sample action 
        self.sample_initialization(flow_a,flow_b,_active_step_id)
        # if user cancelled, do not continue
        if self._sequence_cancelled:
            print("Sequence cancelled by user.")
            return
        # proceed to next step
        self._run_next_step()


    def _run_next_step(self):
        self._temp_hold_start = None  # reset stability timer for new step

        if self._sequence_cancelled:
            print("Sequence cancelled by user.")
            return

        if self._sequence_index >= len(self._sequence_steps): #checks if we are at the end of the flowrate sequence
            print("Sequence finished, setting flowrates to 0.1")

            self.pump1.setFlowrateText.setText("0.1")
            self.pump1.setFlowrate()
            self.pump2.setFlowrateText.setText("0.1")
            self.pump2.setFlowrate()

            self.continuous_log_function(event= "End of sequence reached")

            QtWidgets.QApplication.quit()
            return
        
        self._active_step_id += 1
        step_id = self._active_step_id

        step = self._sequence_steps[self._sequence_index]
        self._sequence_index += 1
        print(f"\n---- STEP {self._sequence_index} ----")

            
        target_temp = float(step["temperature"])
        self._next_flow_a = float(step["flow_rate_a"])
        self._next_flow_b = float(step["flow_rate_b"])
        self._next_delay_min = float(step["steady_state_delay"])

        print(f"Setting target temperature {target_temp} °C ...")
        self.thermo.setpoint_1(target_temp * self.a)

        QtCore.QTimer.singleShot(5000, lambda: self._check_temperature(target_temp,step_id))

    
    def _check_temperature(self, target_temp,step_id): #checks temperature stability before continuing
        if self._sequence_cancelled or step_id != self._active_step_id:
            # stop the sequene if the check belongs to an old step (stops alternating temperature error)
            return

        current_temp = self.safe_read_temp()
        print(f"Current Temp: {current_temp:.1f} °C | Target: {target_temp:.1f} °C")

        if abs(current_temp - target_temp) <= self.tolerance:
            if self._temp_hold_start is None:
                self._temp_hold_start = time.time()
            elif time.time() - self._temp_hold_start >= self.stability_time:
                print(f"Temperature stable at {target_temp} °C for {self.stability_time}s — continuing.")
                self._continue_after_temperature()
                return
        else:
            self._temp_hold_start = None  # reset timer if out of range

        # Check again after 30 seconds
        QtCore.QTimer.singleShot(30000, lambda: self._check_temperature(target_temp,step_id))

    def _continue_after_temperature(self):
        flow_a = self._next_flow_a
        flow_b = self._next_flow_b
        delay = self._next_delay_min # minutes

        MAX_FLOW_RATE = 5
        if flow_a > MAX_FLOW_RATE or flow_b > MAX_FLOW_RATE:
            print(f"Emergency Stop: Flow rate too high! (A: {flow_a}, B: {flow_b})")
            self.handle_stop_sequence()
            QtWidgets.QMessageBox.critical(self, "Emergency Stop",
            f"Flow rate exceeded safe limit!\nPump A: {flow_a}, Pump B: {flow_b}")
            return

        self.pump1.setFlowrateText.setText(str(flow_a))
        self.setFlowrates(self.pump1)

        self.pump2.setFlowrateText.setText(str(flow_b))
        self.setFlowrates(self.pump2)

        print(f"Pumps set: A={flow_a} mL/min | B={flow_b} mL/min | Steady state = {delay:.1f} min")

        self.continuous_log_function(event="Flow Rate Change")

        current_step = self._sequence_index
        current_flow_a = flow_a
        current_flow_b = flow_b

        QtCore.QTimer.singleShot(
            int(delay * 60000), #delay in ms
            lambda: (
                self.sample_initialization(current_flow_a, current_flow_b, current_step),
                self._run_next_step()
            )
        )

        

if __name__ == "__main__":
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = mainWindow()
    MainWindow.setupUi(MainWindow)
    MainWindow.setMinimumSize(1200, 600)
    MainWindow.show()

    ## keyboard interrupt handler (ctrl + c)
    def handle_manual_iterrupt(sig,frame):
        print("Manual Interrupt received")
        QtWidgets.QApplication.quit()

    signal.signal(signal.SIGINT, handle_manual_iterrupt)  

    timer = QtCore.QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)  # allows Ctrl+C to be processed
#### all code runs before the gui boots
    sys.exit(app.exec_())
#### all code runs after the gui closes

