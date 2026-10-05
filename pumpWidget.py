from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox
from PyQt5.QtSerialPort import QSerialPortInfo
import serial
import teledyne_pump
import milliGAT_pump
import chemyxFusion4kX
import chemyxFusion6kX
import jasco2080
import datetime
import json
import os

CALIBRATION_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_history.json")
CALIBRATION_HISTORY_LENGTH = 5 # saved calibrations kept per pump

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

        self.calibrationFactorLabel = QtWidgets.QLabel("Calibration factor:")
        self.calibrationFactorLabel.setFixedSize(120, 20)
        self.calibrationFactorLabel.setHidden(True)
        self.calibrationFactorText = QtWidgets.QLineEdit(self)
        self.calibrationFactorText.setFixedSize(75, 20)
        self.calibrationFactorText.setText("1")
        self.calibrationFactorText.setHidden(True)

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

        self.pumpCalibrateButton = QtWidgets.QPushButton("Calibrate")
        self.pumpCalibrateButton.setFixedSize(80, 25)
        self.pumpCalibrateButton.setStyleSheet("background-color: #2f6f9f;" "color: white;" "border-radius:5px")
        self.pumpCalibrateButton.setHidden(True)

        self.calibrationMethodCombo = QtWidgets.QComboBox(self)
        self.calibrationMethodCombo.addItems(["Droplet counter", "Mass balance"])
        self.calibrationMethodCombo.setToolTip("Calibration strategy")
        self.calibrationMethodCombo.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.calibrationMethodCombo.setFixedSize(120, 20)
        self.calibrationMethodCombo.setHidden(True)

        self.calibrationHistoryCombo = QtWidgets.QComboBox(self)
        self.calibrationHistoryCombo.setToolTip("Last saved calibrations for this pump name - select one to apply it")
        self.calibrationHistoryCombo.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.calibrationHistoryCombo.setFixedSize(175, 20)
        self.calibrationHistoryCombo.setHidden(True)

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
        self.grid.addWidget(self.calibrationFactorLabel, 12, 0)
        self.grid.addWidget(self.calibrationFactorText, 13, 0)
        self.grid.addWidget(self.pumpCalibrateButton, 13, 1)
        self.grid.addWidget(self.calibrationMethodCombo, 14, 0, 1, 2)
        self.grid.addWidget(self.calibrationHistoryCombo, 15, 0, 1, 2)
        self.grid.addWidget(self.pumpStartButton, 16, 0)
        self.grid.addWidget(self.pumpStartButton_1, 16, 0)
        self.grid.addWidget(self.pumpStartButton_2, 16, 4)
        self.grid.addWidget(self.pumpStopButton, 17, 0)
        self.grid.addWidget(self.pumpStopButton_1, 17, 0)
        self.grid.addWidget(self.pumpStopButton_2, 17, 4)
        self.grid.setHorizontalSpacing(5)
        self.grid.setVerticalSpacing(5)
        self.grid.setAlignment(QtCore.Qt.AlignCenter)

        self.comPort.activated.connect(self.connect)
        self.pumpModelCombo.activated.connect(lambda: self.formatWidget(pump=self.pumpModelCombo.currentText()))
        self.setFlowrateText.returnPressed.connect(self.setFlowrate)
        self.pumpStartButton.pressed.connect(self.start)
        self.pumpStopButton.pressed.connect(self.stop)
        self.pumpCalibrateButton.pressed.connect(self.calibrate)
        self.calibrationHistoryCombo.activated.connect(self._apply_saved_calibration)
        self.nameEdit.textChanged.connect(self._on_name_changed)
        self._refresh_calibration_history()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.updatePorts)
        self.timer.start()

    def _on_name_changed(self, text):
        name = text.strip() or self._default_name
        self.pumpName = f"{self._name_prefix}{name}"
        self.pumpGroupBox.setTitle(self.pumpName)
        self._refresh_calibration_history()

    def _calibration_history_key(self):
        # Saved calibrations are stored against the pump name
        return self.nameEdit.text().strip() or self._default_name

    def _load_calibration_history(self):
        try:
            with open(CALIBRATION_HISTORY_FILE, "r", encoding="utf-8") as file_handle:
                history = json.load(file_handle)
            return history if isinstance(history, dict) else {}
        except (OSError, ValueError):
            return {}

    def _refresh_calibration_history(self):
        entries = self._load_calibration_history().get(self._calibration_history_key(), [])
        self.calibrationHistoryCombo.clear()
        self.calibrationHistoryCombo.addItem("Saved calibrations")
        for entry in entries:
            self.calibrationHistoryCombo.addItem(f"{entry['factor']:.4f}  ({entry['date']})", entry["factor"])

    def _apply_saved_calibration(self, index):
        factor = self.calibrationHistoryCombo.itemData(index)
        if factor is not None:
            self.calibrationFactorText.setText(f"{factor:.4f}")

    def save_calibration(self, factor, method=""):
        """Apply a new calibration factor and add it to this pump's saved calibrations (newest first)."""
        factor = float(factor)
        self.calibrationFactorText.setText(f"{factor:.4f}")

        history = self._load_calibration_history()
        entries = history.get(self._calibration_history_key(), [])
        entries.insert(0, {
            "factor": round(factor, 4),
            "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "method": method,
        })
        history[self._calibration_history_key()] = entries[:CALIBRATION_HISTORY_LENGTH]
        try:
            with open(CALIBRATION_HISTORY_FILE, "w", encoding="utf-8") as file_handle:
                json.dump(history, file_handle, indent=2)
        except OSError as e:
            print(f"Could not save calibration history: {e}")
        self._refresh_calibration_history()
        self.calibrationHistoryCombo.setCurrentIndex(1)

    def _get_requested_flowrate(self):
        try:
            flow_text = self.setFlowrateText.text().strip()
            return float(flow_text) if flow_text else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def _get_calibration_factor(self):
        try:
            factor_text = self.calibrationFactorText.text().strip()
            factor = float(factor_text) if factor_text else 1.0
            if factor <= 0:
                return 1.0
            return factor
        except (ValueError, AttributeError):
            return 1.0

    def _get_command_flowrate(self):
        requested_flow = self._get_requested_flowrate()
        calibration_factor = self._get_calibration_factor()
        return requested_flow * calibration_factor

    def get_target_flowrate(self):
        return self._get_requested_flowrate()

    def formatWidget(self, pump):
        if pump == "Teledyne" or pump == "Jasco PU2080":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(340)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.calibrationFactorLabel.setHidden(False)
            self.calibrationFactorText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
            self.pumpCalibrateButton.setHidden(False)
        elif pump == "MilliGAT LF" or pump == "MilliGAT HF":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(340)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.pumpAddressLabel.setHidden(False)
            self.pumpAddressText.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.calibrationFactorLabel.setHidden(False)
            self.calibrationFactorText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
            self.pumpCalibrateButton.setHidden(False)
        elif pump == "Chemyx Nexus 4000" or pump == "Chemyx Fusion 6000X":
            self.resetWidget()
            self.pumpGroupBox.setMaximumHeight(380)
            self.pumpGroupBox.setMaximumWidth(200)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.setFlowrateLabel.setHidden(False)
            self.setFlowrateText.setHidden(False)
            self.calibrationFactorLabel.setHidden(False)
            self.calibrationFactorText.setHidden(False)
            self.pumpStartButton.setHidden(False)
            self.pumpStopButton.setHidden(False)
            self.setSyrSizeLabel.setHidden(False)
            self.setSyrCombo.setHidden(False)
            self.pumpCalibrateButton.setHidden(False)
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
            self.pumpCalibrateButton.setHidden(False)
        else:
            self.resetWidget()

        # The calibration strategy selector goes wherever the calibrate button is, on its own row
        self.calibrationMethodCombo.setHidden(self.pumpCalibrateButton.isHidden())
        if not self.pumpCalibrateButton.isHidden():
            self.pumpGroupBox.setMaximumHeight(self.pumpGroupBox.maximumHeight() + 30)

        # Saved calibrations sit under the calibration factor they apply to
        self.calibrationHistoryCombo.setHidden(self.calibrationFactorText.isHidden())
        if not self.calibrationFactorText.isHidden():
            self.pumpGroupBox.setMaximumHeight(self.pumpGroupBox.maximumHeight() + 25)

    def calibrate(self):
        try:
            if self.calibrationMethodCombo.currentText() == "Mass balance":
                from mass_calibration import BalanceSettingsDialog, MassBalanceCalibration
                dialog = BalanceSettingsDialog(self)
                if dialog.exec() != QDialog.Accepted:
                    return
                self.active_calibration = MassBalanceCalibration(widget=self, **dialog.settings())
            else:
                from droplet_calibration import DropletCounter
                controller = self.parent()
                driver = getattr(controller, "fractioncollector", None)
                self.active_calibration = DropletCounter(widget=self, driver=driver)

        except Exception as e:
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Calibration Error")
            msgbox.setText("Could not start calibration: " + str(e))
            msgbox.setFixedSize(300, 100)
            msgbox.exec()
        
    def resetWidget(self):
        self.comPortLabel.setHidden(True)
        self.comPort.setHidden(True)
        self.pumpAddressLabel.setHidden(True)
        self.pumpAddressText.setHidden(True)
        self.setFlowrateLabel.setHidden(True)
        self.setFlowrateText.setHidden(True)
        self.calibrationFactorLabel.setHidden(True)
        self.calibrationFactorText.setHidden(True)
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
        self.pumpCalibrateButton.setHidden(True)
        self.calibrationMethodCombo.setHidden(True)
        self.calibrationHistoryCombo.setHidden(True)
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
        flowRate = self._get_command_flowrate()
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        try:
            if pumpModel == "Teledyne":
                self.pumpObj.setFlowrate(str(flowRate))
            elif pumpModel == "Jasco PU2080":
                self.pumpObj.set_flow(flowRate)
            elif pumpModel == 'MilliGAT HF':
                self.pumpObj.set_flow_rate(flowRate, pump_type='HF')
            elif pumpModel == "MilliGAT LF":
                self.pumpObj.set_flow_rate(flowRate, pump_type='LF')
            elif pumpModel == 'Chemyx Fusion 6000X':
                self.pumpObj.setRate(rate=str(flowRate), x=0)
        except:
            print('No pump connected')

    def start(self):
        flowRate = self._get_command_flowrate()
        pumpModel = self.pumpModelCombo.currentText()
        COMPort = self.comPort.currentText()
        if pumpModel == "Teledyne":
            self.pumpObj.start()
        elif pumpModel == "Jasco PU2080":
            self.pumpObj.set_flow(flowRate)
            self.pumpObj.start()
        elif pumpModel == "MilliGAT HF":
            self.pumpObj.set_flow_rate(flowRate, pump_type='HF') # No 'start' command for MilliGAT, starts when a flow rate is sent, so send flow rate in current text field
        elif pumpModel == "MilliGAT LF":
            self.pumpObj.set_flow_rate(flowRate, pump_type='LF') 
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
        
