from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox
from PyQt5.QtSerialPort import QSerialPortInfo
import serial
import teledyne_pump
import milliGAT_pump
import chemyxFusion4kX
import chemyxFusion6kX
import jasco2080

class PumpControl(QtWidgets.QWidget):
    def __init__(self, parent, pumpName:any):
        super(PumpControl, self).__init__(parent)

        self._name_prefix = "Pump - "
        self._default_name = str(pumpName)
        self.pumpName = f"{self._name_prefix}{self._default_name}"
        self.pumpGroupBox = QtWidgets.QGroupBox(self.pumpName)
        self.nameLabel = QtWidgets.QLabel("Name:")
        self.nameLabel.setFixedSize(50, 20)
        self.nameEdit = QtWidgets.QLineEdit(self)
        self.nameEdit.setFixedSize(120, 20)
        self.nameEdit.setText(self._default_name)
        self.comPortLabel = QtWidgets.QLabel("COMPort")
        self.comPortLabel.setFixedSize(50, 20)
        self.comPortLabel.setHidden(True)
        self.comPort = QtWidgets.QComboBox(self)
        self.comPort.addItems([ port.portName() for port in QSerialPortInfo().availablePorts() ])
        self.comPort.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.comPort.setFixedSize(60, 20)
        self.comPort.setHidden(True)

        self.pumpModelLabel = QtWidgets.QLabel("Pump type: ")
        self.pumpModelLabel.setFixedSize(75, 20)
        self.pumpModelCombo = QtWidgets.QComboBox(self)
        self.pumpModelCombo.addItems([ "", "Teledyne", "MilliGAT LF", "MilliGAT HF", "Chemyx Nexus 4000", "Chemyx Fusion 6000X", "Chemyx Fusion 4000X", "Jasco PU2080"])
        self.pumpModelCombo.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.pumpModelCombo.setFixedSize(100, 20)

        self.pumpAddressLabel = QtWidgets.QLabel("Pump address: ")
        self.pumpAddressLabel.setHidden(True)
        self.pumpAddressText = QtWidgets.QLineEdit(self)
        self.pumpAddressText.setFixedSize(30, 20)
        self.pumpAddressText.setHidden(True)

        self.setFlowrateLabel = QtWidgets.QLabel("Flow rate [mL/min]: ")
        self.setFlowrateLabel.setFixedSize(150, 30)
        self.setFlowrateLabel.setHidden(True)
        self.setFlowrateText = QtWidgets.QLineEdit(self)
        self.setFlowrateText.setFixedSize(75, 20)
        self.setFlowrateText.setHidden(True)

        self.setSyrSizeLabel = QtWidgets.QLabel('Syringe size [mL]')
        self.setSyrSizeLabel.setFixedSize(100, 30)
        self.setSyrSizeLabel.setHidden(True)
        self.setSyrCombo = QtWidgets.QComboBox(self)
        self.setSyrCombo.setFixedSize(60, 20)
        self.setSyrCombo.addItems(["", "25 mL", "50 mL", "100 mL", "200 mL"])
        self.setSyrCombo.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.setSyrCombo.setHidden(True)

        self.setSyrSizeLabel_1 = QtWidgets.QLabel('Syringe 1 size [mL]')
        self.setSyrSizeLabel_1.setFixedSize(100, 20)
        self.setSyrSizeLabel_1.setHidden(True)
        self.setSyrCombo_1 = QtWidgets.QComboBox(self)
        self.setSyrCombo_1.setFixedSize(60, 20)
        self.setSyrCombo_1.addItems(["", "25 mL", "50 mL", "100 mL", "200 mL"])
        self.setSyrCombo_1.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.setSyrCombo_1.setHidden(True)

        self.setFlowrateLabel_1 = QtWidgets.QLabel("Flow rate 1 [mL/min]: ")
        self.setFlowrateLabel_1.setFixedSize(150, 20)
        self.setFlowrateLabel_1.setHidden(True)
        self.setFlowrateText_1 = QtWidgets.QLineEdit(self)
        self.setFlowrateText_1.setFixedSize(75, 20)
        self.setFlowrateText_1.setHidden(True)

        self.pumpStartButton_1 = QtWidgets.QPushButton("RUN")
        self.pumpStartButton_1.setFixedSize(50, 25)
        self.pumpStartButton_1.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")
        self.pumpStartButton_1.setHidden(True)

        self.pumpStopButton_1 = QtWidgets.QPushButton("STOP")
        self.pumpStopButton_1.setFixedSize(50, 25)
        self.pumpStopButton_1.setStyleSheet("background-color: #ab1b1b;" "color: white;" "border-radius:5px")
        self.pumpStopButton_1.setHidden(True)

        self.setSyrSizeLabel_2 = QtWidgets.QLabel('Syringe 2 size [mL]')
        self.setSyrSizeLabel_2.setFixedSize(100, 20)
        self.setSyrSizeLabel_2.setHidden(True)
        self.setSyrCombo_2 = QtWidgets.QComboBox(self)
        self.setSyrCombo_2.setFixedSize(60, 20)
        self.setSyrCombo_2.addItems(["", "20 mL", "50 mL", "100 mL", "200 mL"])
        self.setSyrCombo_2.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.setSyrCombo_2.setHidden(True)

        self.setFlowrateLabel_2 = QtWidgets.QLabel("Flow rate 2 [mL/min]: ")
        self.setFlowrateLabel_2.setFixedSize(150, 20)
        self.setFlowrateLabel_2.setHidden(True)
        self.setFlowrateText_2 = QtWidgets.QLineEdit(self)
        self.setFlowrateText_2.setFixedSize(75, 20)
        self.setFlowrateText_2.setHidden(True)

        self.pumpStartButton_2 = QtWidgets.QPushButton("RUN")
        self.pumpStartButton_2.setFixedSize(50, 25)
        self.pumpStartButton_2.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")
        self.pumpStartButton_2.setHidden(True)

        self.pumpStopButton_2 = QtWidgets.QPushButton("STOP")
        self.pumpStopButton_2.setFixedSize(50, 25)
        self.pumpStopButton_2.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")
        self.pumpStopButton_2.setHidden(True)

        self.pumpStartButton = QtWidgets.QPushButton("RUN")
        self.pumpStartButton.setFixedSize(50, 25)
        self.pumpStartButton.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")
        self.pumpStartButton.setHidden(True)

        self.pumpStopButton = QtWidgets.QPushButton("STOP")
        self.pumpStopButton.setFixedSize(50, 25)
        self.pumpStopButton.setStyleSheet("background-color: #ab1b1b;" "color: white;" "border-radius:5px")
        self.pumpStopButton.setHidden(True)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.grid = QtWidgets.QGridLayout()
        self.pumpGroupBox.setLayout(self.grid)
        self.pumpGroupBox.setMaximumHeight(300)
        self.pumpGroupBox.setMaximumWidth(200)
        self.layout.addWidget(self.pumpGroupBox)
        self.grid.addWidget(self.nameLabel, 0, 0)
        self.grid.addWidget(self.nameEdit, 1, 0, 1, 2)
        self.grid.addWidget(self.pumpModelLabel, 2, 0, QtCore.Qt.AlignTop)
        self.grid.addWidget(self.pumpModelCombo, 3, 0, QtCore.Qt.AlignTop)
        self.grid.addWidget(self.comPortLabel, 4, 0)
        self.grid.addWidget(self.comPort, 5, 0)
        self.grid.addWidget(self.pumpAddressLabel, 6, 0)
        self.grid.addWidget(self.pumpAddressText, 7, 0)
        self.grid.addWidget(self.setSyrSizeLabel, 8, 0)
        self.grid.addWidget(self.setSyrSizeLabel_1, 8, 0)
        self.grid.addWidget(self.setSyrSizeLabel_2, 8, 4)
        self.grid.addWidget(self.setSyrCombo, 9, 0)
        self.grid.addWidget(self.setSyrCombo_1, 9, 0)
        self.grid.addWidget(self.setSyrCombo_2, 9, 4)
        self.grid.addWidget(self.setFlowrateLabel, 10, 0)
        self.grid.addWidget(self.setFlowrateLabel_1, 10, 0, 1, 2)
        self.grid.addWidget(self.setFlowrateLabel_2, 10, 4, 1, 2)
        self.grid.addWidget(self.setFlowrateText, 11, 0)
        self.grid.addWidget(self.setFlowrateText_1, 11, 0, 1, 2)
        self.grid.addWidget(self.setFlowrateText_2, 11, 4, 1, 2)
        self.grid.addWidget(self.pumpStartButton, 12, 0)
        self.grid.addWidget(self.pumpStartButton_1, 12, 0)
        self.grid.addWidget(self.pumpStartButton_2, 12, 4)
        self.grid.addWidget(self.pumpStopButton, 13, 0)
        self.grid.addWidget(self.pumpStopButton_1, 13, 0)
        self.grid.addWidget(self.pumpStopButton_2, 13, 4)
        self.grid.setHorizontalSpacing(5)
        self.grid.setVerticalSpacing(5)
        self.grid.setAlignment(QtCore.Qt.AlignCenter)

        self.comPort.activated.connect(self.connect)
        self.pumpModelCombo.activated.connect(lambda: self.formatWidget(pump=self.pumpModelCombo.currentText()))
        self.setFlowrateText.returnPressed.connect(self.setFlowrate)
        self.pumpStartButton.pressed.connect(self.start)
        self.pumpStopButton.pressed.connect(self.stop)
        self.nameEdit.textChanged.connect(self._on_name_changed)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.updatePorts)
        self.timer.start()

    def _on_name_changed(self, text):
        name = text.strip() or self._default_name
        self.pumpName = f"{self._name_prefix}{name}"
        self.pumpGroupBox.setTitle(self.pumpName)

    def formatWidget(self, pump):
        if pump == "Teledyne" or pump == "Jasco PU2080":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(300)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
        elif pump == "MilliGAT LF" or pump == "MilliGAT HF":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(300)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.pumpAddressLabel.setHidden(False)
            self.pumpAddressText.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
        elif pump == "Chemyx Nexus 4000" or pump == "Chemyx Fusion 6000X":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(350)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
            self.setSyrSizeLabel.setHidden(False)
            self.setSyrCombo.setHidden(False)
        elif pump == "Chemyx Fusion 4000X":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(350)
            self.pumpGroupBox.setMaximumWidth(400)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.setFlowrateLabel_1.setHidden(False)
            self.setFlowrateText_1.setHidden(False)
            self.setFlowrateLabel_2.setHidden(False)
            self.setFlowrateText_2.setHidden(False)
            self.pumpStartButton_1.setHidden(False)
            self.pumpStopButton_1.setHidden(False)
            self.pumpStartButton_2.setHidden(False)
            self.pumpStopButton_2.setHidden(False)
            self.setSyrSizeLabel_1.setHidden(False)
            self.setSyrCombo_1.setHidden(False)
            self.setSyrSizeLabel_2.setHidden(False)
            self.setSyrCombo_2.setHidden(False)
        else:
            self.resetWidget()
        
    def resetWidget(self):
        self.comPortLabel.setHidden(True)
        self.comPort.setHidden(True)
        self.pumpAddressLabel.setHidden(True)
        self.pumpAddressText.setHidden(True)
        self.setFlowrateLabel.setHidden(True)
        self.setFlowrateText.setHidden(True)
        self.pumpStartButton.setHidden(True)
        self.pumpStopButton.setHidden(True)
        self.setSyrSizeLabel.setHidden(True)
        self.setSyrCombo.setHidden(True)
        self.setFlowrateLabel_1.setHidden(True)
        self.setFlowrateText_1.setHidden(True)
        self.setFlowrateLabel_2.setHidden(True)
        self.setFlowrateText_2.setHidden(True)
        self.pumpStartButton_1.setHidden(True)
        self.pumpStopButton_1.setHidden(True)
        self.pumpStartButton_2.setHidden(True)
        self.pumpStopButton_2.setHidden(True)
        self.setSyrSizeLabel_1.setHidden(True)
        self.setSyrCombo_1.setHidden(True)
        self.setSyrSizeLabel_2.setHidden(True)
        self.setSyrCombo_2.setHidden(True)

    def updatePorts(self):
        currentPort = self.comPort.currentText()
        comport_num = self.comPort.currentText()
        portsListTemp = QSerialPortInfo.availablePorts()
        if portsListTemp != QSerialPortInfo.availablePorts():
            self.comPort.clear()
            self.comPort.addItems([ port.portName() for port in QSerialPortInfo().availablePorts() ])
            self.comPort.setCurrentText(currentPort)

    def connect(self):
        pumpConnectSuccess = 1
        address = self.pumpAddressText.text()
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        COM_number = int(COMPort.replace("COM", "")) # removes 'com' from COMPort. e.g. COMPort = 'COM3', COM_number = 3

        if pumpModel == "Teledyne":
            self.pumpObj = teledyne_pump.teledynePump()
            self.pumpObj.connect(COMPort)

        elif pumpModel == "Jasco PU2080":
            self.pumpObj = jasco2080.JascoPU2080(COM_number)
        
        elif pumpModel == "MilliGAT HF":
            if self.pumpAddressText.text() == '':
                pumpConnectSuccess = 0
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("Pump address required")
                msgbox.setText("Please add a pump address 'A', 'B', or 'C'")
                msgbox.setFixedSize(250, 75)
                msgbox.exec()
            else:
                self.pumpObj = milliGAT_pump.Milligat(name=address, ser=serial.Serial(COMPort, 9600))
        elif pumpModel == "MilliGAT LF":
            if self.pumpAddressText.text() == '':
                pumpConnectSuccess = 0
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("Pump address required")
                msgbox.setText("Please add a pump address, e.g. 'A', 'B'...")
                msgbox.setFixedSize(250, 75)
                msgbox.exec()
            else:
                self.pumpObj = milliGAT_pump.Milligat(name=address, ser=serial.Serial(COMPort, 9600))
        elif pumpModel == 'Chemyx Nexus 4000X':
            self.pumpObj = chemyxFusion4kX.ChemyxFusion4kXPump(str(COMPort))
        elif pumpModel == 'Chemyx Fusion 6000X':
            self.pumpObj = chemyxFusion6kX.ChemyxFusion6kXPump(port=str(COMPort), baudrate=9600, x=0)
        elif pumpModel == 'Chemyx Fusion 4000X':
            self.pumpObj = chemyxFusion4kX.ChemyxFusion4kXPump(str(COMPort))
        else:
            print('No model selected')
        if pumpConnectSuccess == 1:
            print('Pump created: ' + str(self.pumpName))

    def setFlowrate(self):
        flowRate = self.setFlowrateText.text()
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        try:
            if pumpModel == "Teledyne":
                self.pumpObj.setFlowrate(flowRate)
            elif pumpModel == "jasco PU2080":
                self.pumpObj.set_flow_rate(float(flowRate))
            elif pumpModel == 'MilliGAT HF':
                self.pumpObj.set_flow_rate(float(flowRate), pump_type='HF')
            elif pumpModel == "MilliGAT LF":
                self.pumpObj.set_flow_rate(float(flowRate), pump_type="LF")
            elif pumpModel == 'Chemyx Fusion 6000X':
                self.pumpObj.setRate(rate=flowRate, x=0)
        except:
            print('No pump connected')

    def start(self):
        flowRate = self.setFlowrateText.text()
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        if pumpModel == "Teledyne":
            self.pumpObj.start()
        elif pumpModel == "Jasco PU2080":
            self.pumpObj.set_flow(float(flowRate))
            self.pumpObj.start()
        elif pumpModel == "MilliGAT HF":
            self.pumpObj.set_flow_rate(float(flowRate), pump_type='HF') # No 'start' command for MilliGAT, starts when a flow rate is sent, so send flow rate in current text field
        elif pumpModel == "MilliGAT LF":
            self.pumpObj.set_flow_rate(float(flowRate), pump_type='LF') 
        elif pumpModel == "Chemyx Fusion 6000X":
            self.pumpObj.startPump()
        else:
            print('No model selected')

    def stop(self):
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        if pumpModel == "Teledyne":
            self.pumpObj.stop()
        elif pumpModel == "Jasco PU2080":
            self.pumpObj.stop()
        elif pumpModel == "MilliGAT HF":
            self.pumpObj.stop_pump()
        elif pumpModel == "MilliGAT LF":
            self.pumpObj.stop_pump()
        elif pumpModel == "Chemyx Fusion 6000X":
            self.pumpObj.stopPump()
        else:
            print('No model selected')

    def read_flow(self):
        """Read current flow rate from pump. Returns flow in mL/min or 0.0 if not available - designed for jasco - will need to add individual pump code yourself if needed."""
        pumpModel = self.pumpModelCombo.currentText()
        try:
            if pumpModel == "Jasco PU2080":
                result = self.pumpObj.read_flow()
                return result
            elif pumpModel == "Teledyne":
                # Teledyne doesn't have hardware readback; return set value from UI
                try:
                    return float(self.setFlowrateText.text()) if self.setFlowrateText.text() else 0.0
                except (ValueError, AttributeError):
                    return 0.0
            elif pumpModel in ("MilliGAT HF", "MilliGAT LF"):
                # MilliGAT doesn't have hardware readback; return set value from UI
                try:
                    return float(self.setFlowrateText.text()) if self.setFlowrateText.text() else 0.0
                except (ValueError, AttributeError):
                    return 0.0
            elif pumpModel in ("Chemyx Fusion 6000X", "Chemyx Fusion 4000X", "Chemyx Nexus 4000"):
                # Chemyx pumps don't have hardware readback; return set value from UI
                try:
                    return float(self.setFlowrateText.text()) if self.setFlowrateText.text() else 0.0
                except (ValueError, AttributeError):
                    return 0.0
            else:
                return 0.0
        except Exception as e:
            print(f"Error reading flow from {pumpModel}: {e}")
            return 0.0
        

    def read_pressure(self):
        """Read current pressure from pump. Returns pressure in bar or 0.0 if not available - designed for jasco - will need to add individual pump code yourself if needed."""
        pumpModel = self.pumpModelCombo.currentText()
        try:
            if pumpModel == "Jasco PU2080":
                result = self.pumpObj.read_pressure()
                return result
            else:
                return 0.0
        except Exception as e:
            print(f"Error reading pressure from {pumpModel}: {e}")
            return 0.0
        
