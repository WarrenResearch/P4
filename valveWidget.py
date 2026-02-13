from PyQt5 import QtWidgets, QtCore
from PyQt5.QtSerialPort import QSerialPortInfo
import serial
import valve_controller_selection
import valve_controller_switching
import rheodyne232
import viciValve
import time
import threading

class ValveControl(QtWidgets.QWidget):
    def __init__(self, parent, valveName:any):
        super(ValveControl, self).__init__(parent)

        self._name_prefix = "Valve - "
        self._default_name = str(valveName)
        self.valveName = f"{self._name_prefix}{self._default_name}"
        self.valveGroupBox = QtWidgets.QGroupBox(self.valveName)
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

        self.valveTypeLabel = QtWidgets.QLabel("Valve type: ")
        self.valveTypeLabel.setFixedSize(75, 20)
        self.valveTypeCombo = QtWidgets.QComboBox(self)
        self.valveTypeCombo.addItems([ "", "BioChem 6way selection", "BioChem 8way selection", "Rheodyne 2pos switching", "Vici 2pos switching", "BioChem 6way switching"])
        self.valveTypeCombo.setStyleSheet("background-color: rgb(210, 210, 210);" "color: black;" "border-radius:5px")
        self.valveTypeCombo.setFixedSize(100, 20)

        self.positionLabel = QtWidgets.QLabel("Position: ")
        self.positionLabel.setFixedSize(150, 30)
        self.positionLabel.setHidden(True)
        self.positionText = QtWidgets.QLineEdit(self)
        self.positionText.setFixedSize(75, 20)
        self.positionText.setHidden(True)

        self.positionAButton = QtWidgets.QPushButton("Position A")
        self.positionAButton.setFixedSize(50, 25)
        self.positionAButton.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.positionAButton.setHidden(True)

        self.positionBButton = QtWidgets.QPushButton("Position B")
        self.positionBButton.setFixedSize(50, 25)
        self.positionBButton.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.positionBButton.setHidden(True)

        self.sampleButton = QtWidgets.QPushButton("Sample")
        self.sampleButton.setFixedSize(50, 25)
        self.sampleButton.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.sampleButton.setHidden(True)

        self.setDelayButton = QtWidgets.QPushButton("Set Delay")
        self.setDelayButton.setFixedSize(50, 25)
        self.setDelayButton.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.setDelayButton.setHidden(True)

        self.DelayTimeLabel = QtWidgets.QLabel("Delay Time:")
        self.DelayTimeLabel.setHidden(True)

        self.DelayTimeLineEdit = QtWidgets.QLineEdit()
        self.DelayTimeLineEdit.setMaximumSize(30, 25)
        self.DelayTimeLineEdit.setText('10')
        self.DelayTimeLineEdit.setHidden(True)

        self.port1Button = QtWidgets.QPushButton("Port 1")
        self.port1Button.setFixedSize(50, 25)
        self.port1Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port1Button.setHidden(True)

        self.port2Button = QtWidgets.QPushButton("Port 2")
        self.port2Button.setFixedSize(50, 25)
        self.port2Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port2Button.setHidden(True)

        self.port3Button = QtWidgets.QPushButton("Port 3")
        self.port3Button.setFixedSize(50, 25)
        self.port3Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port3Button.setHidden(True)

        self.port4Button = QtWidgets.QPushButton("Port 4")
        self.port4Button.setFixedSize(50, 25)
        self.port4Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port4Button.setHidden(True)

        self.port5Button = QtWidgets.QPushButton("Port 5")
        self.port5Button.setFixedSize(50, 25)
        self.port5Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port5Button.setHidden(True)

        self.port6Button = QtWidgets.QPushButton("Port 6")
        self.port6Button.setFixedSize(50, 25)
        self.port6Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port6Button.setHidden(True)

        self.port7Button = QtWidgets.QPushButton("Port 7")
        self.port7Button.setFixedSize(50, 25)
        self.port7Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port7Button.setHidden(True)

        self.port8Button = QtWidgets.QPushButton("Port 8")
        self.port8Button.setFixedSize(50, 25)
        self.port8Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port8Button.setHidden(True)

        self.nFeedsLabel = QtWidgets.QLabel("Feeds:")
        self.nFeedsLabel.setHidden(True)

        self.nFeedsLineEdit = QtWidgets.QLineEdit()
        self.nFeedsLineEdit.setMaximumSize(30, 25)
        self.nFeedsLineEdit.setText('3')
        self.nFeedsLineEdit.setHidden(True)

        self.distributionModeCheckbox = QtWidgets.QCheckBox("Distribution mode")
        self.distributionModeCheckbox.setHidden(True)

        self.startDistributionButton = QtWidgets.QPushButton("Start")
        self.startDistributionButton.setFixedSize(50, 25)
        self.startDistributionButton.setStyleSheet("background-color: green;" "color: white;" "border-radius:5px")
        self.startDistributionButton.setHidden(True)

        self.stopDistributionButton = QtWidgets.QPushButton("Stop")
        self.stopDistributionButton.setFixedSize(50, 25)
        self.stopDistributionButton.setStyleSheet("background-color: red;" "color: white;" "border-radius:5px")
        self.stopDistributionButton.setHidden(True)

        self.startDistributionButton.pressed.connect(self.startDistribution)
        self.stopDistributionButton.pressed.connect(self.stopDistribution)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.grid = QtWidgets.QGridLayout()
        self.valveGroupBox.setLayout(self.grid)
        self.valveGroupBox.setFixedWidth(250)
        self.valveGroupBox.setMaximumHeight(350)
        self.layout.addWidget(self.valveGroupBox)
        self.grid.addWidget(self.nameLabel, 0, 0)
        self.grid.addWidget(self.nameEdit, 0, 1)
        self.grid.addWidget(self.valveTypeLabel, 1, 0)
        self.grid.addWidget(self.valveTypeCombo, 1, 1)
        self.grid.addWidget(self.comPortLabel, 2, 0)
        self.grid.addWidget(self.comPort, 2, 1)
        self.grid.addWidget(self.positionLabel, 3, 0)
        self.grid.addWidget(self.positionText, 3, 1)
        self.grid.addWidget(self.positionAButton, 4, 0)
        self.grid.addWidget(self.positionBButton, 4, 1)
        self.grid.addWidget(self.DelayTimeLabel, 11, 0)
        self.grid.addWidget(self.DelayTimeLineEdit, 11, 1)
        self.grid.addWidget(self.sampleButton, 12, 0)
        self.grid.addWidget(self.setDelayButton, 12, 1)
        self.grid.addWidget(self.port1Button, 4, 0)
        self.grid.addWidget(self.port2Button, 5, 0)
        self.grid.addWidget(self.port3Button, 6, 0)
        self.grid.addWidget(self.port4Button, 7, 0)
        self.grid.addWidget(self.port5Button, 4, 1)
        self.grid.addWidget(self.port6Button, 5, 1)
        self.grid.addWidget(self.port7Button, 6, 1)
        self.grid.addWidget(self.port8Button, 7, 1)
        self.grid.addWidget(self.nFeedsLabel, 8, 0)
        self.grid.addWidget(self.nFeedsLineEdit, 8, 1)
        self.grid.addWidget(self.distributionModeCheckbox, 9, 0, 1, 2)
        self.grid.addWidget(self.startDistributionButton, 10, 0)
        self.grid.addWidget(self.stopDistributionButton, 10, 1)
        self.grid.setVerticalSpacing(10)
        self.grid.setAlignment(QtCore.Qt.AlignCenter)

        self.comPort.activated.connect(self.connect)
        self.valveTypeCombo.activated.connect(lambda: self.formatWidget(valve=self.valveTypeCombo.currentText()))
        self.nameEdit.textChanged.connect(self._on_name_changed)

        self.port1Button.clicked.connect(self.valveHome)
        self.port2Button.clicked.connect(lambda: self.valveSwitch(position=2))
        self.port3Button.clicked.connect(lambda: self.valveSwitch(position=3))
        self.port4Button.clicked.connect(lambda: self.valveSwitch(position=4))
        self.port5Button.clicked.connect(lambda: self.valveSwitch(position=5))
        self.port6Button.clicked.connect(lambda: self.valveSwitch(position=6))
        self.port7Button.clicked.connect(lambda: self.valveSwitch(position=7))
        self.port8Button.clicked.connect(lambda: self.valveSwitch(position=8))

        self.positionAButton.clicked.connect(lambda: self.valveSwitch(position='A'))
        self.positionBButton.clicked.connect(lambda: self.valveSwitch(position='B'))
        self.sampleButton.clicked.connect(lambda: self.valveSample())
        self.setDelayButton.clicked.connect(lambda: self.writedelaytime())

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.updatePorts)
        self.timer.start()

    def _on_name_changed(self, text):
        name = text.strip() or self._default_name
        self.valveName = f"{self._name_prefix}{name}"
        self.valveGroupBox.setTitle(self.valveName)

    def formatWidget(self, valve):
        if valve == "Rheodyne 2pos switching" or valve == "Vici 2pos switching" or valve == "BioChem 6way switching":
            self.resetWidget()
            self.valveGroupBox.setFixedWidth(225)
            self.valveGroupBox.setMaximumHeight(300)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.positionLabel.setHidden(False)
            self.positionText.setHidden(False)
            self.positionAButton.setHidden(False)
            self.positionBButton.setHidden(False)
            self.sampleButton.setHidden(False)
            self.setDelayButton.setHidden(False)
            self.DelayTimeLabel.setHidden(False)
            self.DelayTimeLineEdit.setHidden(False)

        elif valve == "BioChem 6way selection":
            self.resetWidget()
            self.valveGroupBox.setFixedWidth(225)
            self.valveGroupBox.setMaximumHeight(350)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.positionLabel.setHidden(False)
            self.positionText.setHidden(False)
            self.port1Button.setHidden(False)
            self.port2Button.setHidden(False)
            self.port3Button.setHidden(False)
            self.port4Button.setHidden(False)
            self.port5Button.setHidden(False)
            self.port6Button.setHidden(False)
            self.port7Button.setHidden(False)
            self.port7Button.setDisabled(True)
            self.port7Button.setStyleSheet("background-color: #A3B6C0;" "color: black;" "border-radius:5px")
            self.port8Button.setHidden(False)
            self.port8Button.setDisabled(True)
            self.port8Button.setStyleSheet("background-color: #A3B6C0;" "color: black;" "border-radius:5px")
            self.nFeedsLabel.setHidden(False)
            self.nFeedsLineEdit.setHidden(False)
            self.distributionModeCheckbox.setHidden(False)
            self.startDistributionButton.setHidden(False)
            self.stopDistributionButton.setHidden(False)

        elif valve == "BioChem 8way selection":
            self.resetWidget()
            self.valveGroupBox.setFixedWidth(225)
            self.valveGroupBox.setMaximumHeight(350)
            self.comPortLabel.setHidden(False)
            self.comPort.setHidden(False)
            self.positionLabel.setHidden(False)
            self.positionText.setHidden(False)
            self.port1Button.setHidden(False)
            self.port2Button.setHidden(False)
            self.port3Button.setHidden(False)
            self.port4Button.setHidden(False)
            self.port5Button.setHidden(False)
            self.port6Button.setHidden(False)
            self.port7Button.setHidden(False)
            self.port8Button.setHidden(False)
 
        else:
            self.resetWidget()
        
    def resetWidget(self):
        self.comPortLabel.setHidden(True)
        self.comPort.setHidden(True)
        self.positionLabel.setHidden(True)
        self.positionText.setHidden(True)
        self.positionAButton.setHidden(True)
        self.positionBButton.setHidden(True)
        self.port1Button.setHidden(True)
        self.port2Button.setHidden(True)
        self.port3Button.setHidden(True)
        self.port4Button.setHidden(True)
        self.port5Button.setHidden(True)
        self.port6Button.setHidden(True)
        self.port7Button.setHidden(True)
        self.port7Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port7Button.setDisabled(False)
        self.port8Button.setHidden(True)
        self.port8Button.setStyleSheet("background-color: #2A9BD7;" "color: black;" "border-radius:5px")
        self.port8Button.setDisabled(False)
        self.nFeedsLabel.setHidden(True)
        self.nFeedsLineEdit.setHidden(True)
        self.distributionModeCheckbox.setHidden(True)
        self.startDistributionButton.setHidden(True)
        self.stopDistributionButton.setHidden(True)

    def updatePorts(self):
        currentPort = self.comPort.currentText()
        portsListTemp = QSerialPortInfo.availablePorts()
        if portsListTemp != QSerialPortInfo.availablePorts():
            self.comPort.clear()
            self.comPort.addItems([ port.portName() for port in QSerialPortInfo().availablePorts() ])
            self.comPort.setCurrentText(currentPort)

    def connect(self):
        self.valveType = self.valveTypeCombo.currentText()
        COMPort = self.comPort.currentText()
        if self.valveType == "BioChem 6way selection":
            self.valveObj = valve_controller_selection.selectionValve()
        elif self.valveType == "BioChem 8way selection":
            self.valveObj = valve_controller_selection.selectionValve()
        elif self.valveType == "Rheodyne 2pos switching":
            self.valveObj = rheodyne232.rheodyneValve()
        elif self.valveType == 'Vici 2pos switching':
            self.valveObj = viciValve.viciValve()
        elif self.valveType == "BioChem 6way switching":
            self.valveObj = valve_controller_switching.switchingValve()
        else:
            print('No model selected')
        print('Valve created: ' + str(self.valveName))
        self.valveObj.connect(COMPort)

    def valveSwitch(self, position):
        self.valveType = self.valveTypeCombo.currentText()
        self.positionText.setText(str(position))
        if self.valveType == "BioChem 6way selection":
            self.valveObj.switch(valvePort=position)
        if self.valveType == "BioChem 8way selection":
            self.valveObj.switch(valvePort=position)
        if self.valveType == "BioChem 6way switching":
            self.valveObj.switch()
        if self.valveType == "Rheodyne 2pos switching":
            self.valveObj.switch(valvePort=position)
        if self.valveType == "Vici 2pos switching":
            self.positionText.setText("Position " + str(position))
            if position == 'A':
                self.valveObj.positionA()
            elif position == 'B':
                self.valveObj.positionB()

    def valveSample(self):
        self.valveType = self.valveTypeCombo.currentText()
        self.valveObj.sample()

    def writedelaytime(self):
        if isinstance(int(self.DelayTimeLineEdit.text()), int) and 2 <= int(self.DelayTimeLineEdit.text()) <= 65000:
            self.valveType = self.valveTypeCombo.currentText()
            self.valveObj.writedelaytime(self.DelayTimeLineEdit.text())
        else:
            print('must be integer between 2 and 65000')

    def valveHome(self):
        self.positionText.setText("Home")
        self.valveObj.home()


    def startDistribution(self):
        if self.distributionModeCheckbox.isChecked():
            self.distributionStopThread = False
            self.distributionThread = threading.Thread(target=self.valveDistribution)
            self.distributionThread.start()

    def valveDistribution(self):
        if self.distributionModeCheckbox.isChecked():
            self.valveHome()
            while not self.distributionStopThread:
                if int(self.nFeedsLineEdit.text()) > 6:
                    self.distributionStopThread=True
                    print("Cannot distribute more than 6 feeds")
                else:
                    for i in range(2, int(self.nFeedsLineEdit.text()) + 2):
                        self.valveSwitch(position=i)
                        time.sleep(3)
                    for n in reversed(range(2, int(self.nFeedsLineEdit.text()) + 2)):
                        self.valveSwitch(position=n)
                        time.sleep(3)

    def stopDistribution(self):
        self.distributionStopThread=True
        self.distributionThread.join()
        self.valveHome()