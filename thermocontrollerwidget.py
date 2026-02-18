from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtSerialPort import QSerialPortInfo
import thermocontroller_driver


class ThermocontrollerControl(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ThermocontrollerControl, self).__init__(parent)

        self._name_prefix = "Thermocontroller - "
        self._default_name = "Eurotherm 3216"
        self.thermocontrollerName = f"{self._name_prefix}{self._default_name}"
        self.thermocontrollerObj = None
        self.thermocontrollerGroupBox = QtWidgets.QGroupBox(self.thermocontrollerName)
        
        # Name label and edit
        self.nameLabel = QtWidgets.QLabel("Name:")
        self.nameLabel.setFixedSize(50, 20)
        self.nameEdit = QtWidgets.QLineEdit(self)
        self.nameEdit.setFixedSize(120, 20)
        self.nameEdit.setText(self._default_name)

        # COM Port selection
        self.comPortLabel = QtWidgets.QLabel("COM Port:")
        self.comPortLabel.setFixedSize(70, 20)
        self.comPort = QtWidgets.QComboBox(self)
        self.comPort.addItems([port.portName() for port in QSerialPortInfo().availablePorts()])
        self.comPort.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.comPort.setFixedSize(60, 20)

        # Current temperature readout (read-only)
        self.currentTempLabel = QtWidgets.QLabel("Current Temp [°C]:")
        self.currentTempLabel.setFixedSize(140, 20)
        self.currentTempDisplay = QtWidgets.QLineEdit(self)
        self.currentTempDisplay.setFixedSize(75, 20)
        self.currentTempDisplay.setReadOnly(True)
        self.currentTempDisplay.setText("--")
        self.currentTempDisplay.setStyleSheet("background-color: rgb(230, 230, 230);" "color: black;" "border-radius:5px")

        # Target temperature setting
        self.targetTempLabel = QtWidgets.QLabel("Target Temp [°C]:")
        self.targetTempLabel.setFixedSize(140, 20)
        self.targetTempText = QtWidgets.QLineEdit(self)
        self.targetTempText.setFixedSize(75, 20)
        self.targetTempText.setPlaceholderText("e.g., 350")

        # Connect button
        self.connectButton = QtWidgets.QPushButton("CONNECT")
        self.connectButton.setFixedSize(80, 25)
        self.connectButton.setStyleSheet("background-color: #2A9BD7;" "color: white;" "border-radius:5px")

        # Apply target temperature button
        self.applyButton = QtWidgets.QPushButton("APPLY")
        self.applyButton.setFixedSize(80, 25)
        self.applyButton.setStyleSheet("background-color: #549c55;" "color: white;" "border-radius:5px")

        # Disconnect button
        self.disconnectButton = QtWidgets.QPushButton("DISCONNECT")
        self.disconnectButton.setFixedSize(100, 25)
        self.disconnectButton.setStyleSheet("background-color: #ab1b1b;" "color: white;" "border-radius:5px")

        # Layout setup
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.grid = QtWidgets.QGridLayout()
        self.thermocontrollerGroupBox.setLayout(self.grid)
        self.thermocontrollerGroupBox.setMaximumHeight(300)
        self.thermocontrollerGroupBox.setMaximumWidth(250)
        self.layout.addWidget(self.thermocontrollerGroupBox)

        # Add widgets to grid
        self.grid.addWidget(self.nameLabel, 0, 0)
        self.grid.addWidget(self.nameEdit, 1, 0, 1, 2)
        self.grid.addWidget(self.comPortLabel, 2, 0)
        self.grid.addWidget(self.comPort, 2, 1)
        self.grid.addWidget(self.connectButton, 3, 0, 1, 2)
        self.grid.addWidget(self.currentTempLabel, 4, 0)
        self.grid.addWidget(self.currentTempDisplay, 4, 1)
        self.grid.addWidget(self.targetTempLabel, 5, 0)
        self.grid.addWidget(self.targetTempText, 5, 1)
        self.grid.addWidget(self.applyButton, 6, 0, 1, 2)
        self.grid.addWidget(self.disconnectButton, 7, 0, 1, 2)
        self.grid.setHorizontalSpacing(50)
        self.grid.setVerticalSpacing(5)
        self.grid.setAlignment(QtCore.Qt.AlignTop)

        # Connect signals
        self.connectButton.pressed.connect(self.connect)
        self.applyButton.pressed.connect(self.setTargetTemperature)
        self.disconnectButton.pressed.connect(self.disconnect)
        self.nameEdit.textChanged.connect(self._on_name_changed)

        # Timer for updating current temperature
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.updateCurrentTemperature)
        self.timer.timeout.connect(self.updatePorts)

        # Timer for updating available ports
        self.portUpdateTimer = QtCore.QTimer()
        self.portUpdateTimer.setInterval(2000)
        self.portUpdateTimer.timeout.connect(self.updatePorts)
        self.portUpdateTimer.start()

    def _on_name_changed(self, text):
        name = text.strip() or self._default_name
        self.thermocontrollerName = f"{self._name_prefix}{name}"
        self.thermocontrollerGroupBox.setTitle(self.thermocontrollerName)

    def updatePorts(self):
        """Update available COM ports in the combo box"""
        currentPort = self.comPort.currentText()
        portsListTemp = [port.portName() for port in QSerialPortInfo.availablePorts()]
        comPortItems = [self.comPort.itemText(i) for i in range(self.comPort.count())]
        
        if portsListTemp != comPortItems:
            self.comPort.clear()
            self.comPort.addItems(portsListTemp)
            if currentPort in portsListTemp:
                self.comPort.setCurrentText(currentPort)

    def connect(self):
        """Connect to the thermocontroller on the selected COM port"""
        try:
            comPort = self.comPort.currentText()
            if not comPort:
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("No COM Port Selected")
                msgbox.setText("Please select a COM port")
                msgbox.setFixedSize(250, 75)
                msgbox.exec()
                return
            
            # Create thermocontroller object and connect
            self.thermocontrollerObj = thermocontroller_driver.connect(port=comPort)
            
            if self.thermocontrollerObj and self.thermocontrollerObj.status:
                print(f'Thermocontroller connected on {comPort}')
                self.connectButton.setEnabled(False)
                self.timer.start()
                
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("Connection Successful")
                msgbox.setText(f"Connected to thermocontroller on {comPort}")
                msgbox.setFixedSize(250, 75)
                msgbox.exec()
            else:
                raise Exception("Failed to connect to thermocontroller")
        except Exception as e:
            print(f'Failed to connect: {str(e)}')
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Connection Failed")
            msgbox.setText(f"Could not connect to thermocontroller:\n{str(e)}")
            msgbox.setFixedSize(300, 100)
            msgbox.exec()

    def disconnect(self):
        """Disconnect from the thermocontroller"""
        try:
            if self.thermocontrollerObj:
                self.thermocontrollerObj.shutdown()
                self.thermocontrollerObj = None
                self.timer.stop()
                self.currentTempDisplay.setText("--")
                self.connectButton.setEnabled(True)
                print('Thermocontroller disconnected')
                
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("Disconnected")
                msgbox.setText("Thermocontroller disconnected and set to safe temperature (20°C)")
                msgbox.setFixedSize(300, 75)
                msgbox.exec()
        except Exception as e:
            print(f'Error during disconnect: {str(e)}')

    def setTargetTemperature(self):
        """Set the target temperature on the thermocontroller"""
        try:
            if not self.thermocontrollerObj:
                msgbox = QMessageBox(self)
                msgbox.setWindowTitle("Not Connected")
                msgbox.setText("Please connect to thermocontroller first")
                msgbox.setFixedSize(250, 75)
                msgbox.exec()
                return
            
            targetTemp = float(self.targetTempText.text())
            self.thermocontrollerObj.setpoint_1(targetTemp)
            print(f'Target temperature set to {targetTemp}°C')
            
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Temperature Set")
            msgbox.setText(f"Target temperature set to {targetTemp}°C")
            msgbox.setFixedSize(250, 75)
            msgbox.exec()
        except ValueError:
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Invalid Input")
            msgbox.setText("Please enter a valid temperature value")
            msgbox.setFixedSize(250, 75)
            msgbox.exec()
        except Exception as e:
            print(f'Error setting temperature: {str(e)}')
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Error")
            msgbox.setText(f"Error setting temperature:\n{str(e)}")
            msgbox.setFixedSize(300, 100)
            msgbox.exec()

    def updateCurrentTemperature(self):
        """Update the current temperature display from the thermocontroller"""
        try:
            if self.thermocontrollerObj:
                currentTemp = self.thermocontrollerObj.indicated()
                if currentTemp is not False:
                    self.currentTempDisplay.setText(f"{currentTemp:.1f}")
                else:
                    self.currentTempDisplay.setText("--")
        except Exception as e:
            print(f'Error reading temperature: {str(e)}')
            self.currentTempDisplay.setText("--")


    def safetyShutdown(self):
        if self.thermocontrollerObj and self.thermocontrollerObj.indicated() > 150:
            self.thermocontrollerObj.setpoint_1(20)
            print("Safety shutdown activated: temperature exceeded 150°C, setpoint set to 20°C")