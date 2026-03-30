import json
import os
from PyQt5 import QtWidgets, QtCore
import pumpWidget as pw
import valveWidget as vw
import thermocontrollerwidget as tcw
import fraction_driver as fd

### Class used to define all apparatus available for automated experiments ###

# All pumps and valves are controlled from other scripts by calling to the same instance of the PlatformControl class created in the GUI initialisation.

class PlatformControl(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(PlatformControl, self).__init__(parent)

        self.main = main
        self._layout = QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        self._layout.setHorizontalSpacing(0)
        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 0)
        self._layout.setColumnStretch(2, 0)
        self._layout.setRowStretch(0, 1)
        self._layout.setRowStretch(1, 1)
        self.pumpsTuple = ("Teledyne", "MilliGAT LF", "MilliGAT HF", "Chemyx Nexus 4000", "Chemyx Fusion 6000X", "Chemyx Fusion 4000X", "Jasco PU2080")
        self.valvesTuple = ("BioChem 8way selection", "BioChem 6way selection", "BioChem 6way switching", "Rheodyne 2pos switching", "Vici 2pos switching")

        self.pumpsBox = QtWidgets.QGroupBox("Pumps")
        self.pumpsBox.setMaximumHeight(400)
        self.pumpsBox.setMaximumWidth(2000)
        self.pumpsBoxLayout = QtWidgets.QVBoxLayout(self.pumpsBox)
        self._layout.addWidget(self.pumpsBox, 0, 0, QtCore.Qt.AlignTop)

        self.pumpsHeaderLayout = QtWidgets.QHBoxLayout()
        self.addPumpButton = QtWidgets.QPushButton("Add Pump")
        self.savePlatformButton = QtWidgets.QPushButton("Save Platform")
        self.loadPlatformButton = QtWidgets.QPushButton("Load Platform")
        self.setConfigButton = QtWidgets.QPushButton("Set Monitor Configuration")
        self.pumpsHeaderLayout.addWidget(self.addPumpButton)
        self.pumpsHeaderLayout.addWidget(self.savePlatformButton)
        self.pumpsHeaderLayout.addWidget(self.loadPlatformButton)
        self.pumpsHeaderLayout.addWidget(self.setConfigButton)
        self.pumpsHeaderLayout.addStretch(1)
        self.pumpsBoxLayout.addLayout(self.pumpsHeaderLayout)

        self.pumpsLayout = QtWidgets.QGridLayout()
        self.pumpsLayout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.pumpsBoxLayout.addLayout(self.pumpsLayout)

        self.pump_widgets = []
        self.pump_count = 0
        self.pump_columns = 4
        self.addPumpButton.clicked.connect(self.add_pump)
        self.savePlatformButton.clicked.connect(self.save_platform)
        self.loadPlatformButton.clicked.connect(self.load_platform)
        self.setConfigButton.clicked.connect(self.set_monitor_configuration)


######################################## Valves ########################################
        self.valvesBox = QtWidgets.QGroupBox("Valves")
        self.valvesBox.setMaximumHeight(400)
        self.valvesBox.setMaximumWidth(1400)
        self.valvesBoxLayout = QtWidgets.QVBoxLayout(self.valvesBox)
        self._layout.addWidget(self.valvesBox, 1, 0, QtCore.Qt.AlignTop)

        self.valvesHeaderLayout = QtWidgets.QHBoxLayout()
        self.addValveButton = QtWidgets.QPushButton("Add Valve")
        self.valvesHeaderLayout.addWidget(self.addValveButton)
        self.valvesHeaderLayout.addStretch(1)
        self.valvesBoxLayout.addLayout(self.valvesHeaderLayout)

        self.valvesLayout = QtWidgets.QGridLayout()
        self.valvesLayout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.valvesBoxLayout.addLayout(self.valvesLayout)

        self.valve_widgets = []
        self.valve_count = 0
        self.valve_columns = 4
        self.addValveButton.clicked.connect(self.add_valve)

######################################## Thermocontroller ########################################
        self.thermocontrollerBox = QtWidgets.QGroupBox("Thermocontroller")
        self.thermocontrollerBox.setMaximumHeight(400)
        self.thermocontrollerBox.setMaximumWidth(300)
        self.thermocontrollerBoxLayout = QtWidgets.QVBoxLayout(self.thermocontrollerBox)
        self.thermocontroller = tcw.ThermocontrollerControl(self)
        self.thermocontrollerBoxLayout.addWidget(self.thermocontroller)
        self._layout.addWidget(self.thermocontrollerBox, 0, 2, 1, 1, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)

    ######################################## Sequence targets ########################################
        self.sequenceTargetsBox = QtWidgets.QGroupBox("Reactor Sequence")
        self.sequenceTargetsBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sequenceTargetsBoxLayout = QtWidgets.QVBoxLayout(self.sequenceTargetsBox)
        self._layout.addWidget(self.sequenceTargetsBox, 1, 1)

        self.targetsTable = QtWidgets.QTableWidget(0, 2)
        self.targetsTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.targetsTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.targetsTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.sequenceTargetsBoxLayout.addWidget(self.targetsTable)

        self.tableButtonsLayout = QtWidgets.QHBoxLayout()
        self.addRowButton = QtWidgets.QPushButton("Add row")
        self.removeRowButton = QtWidgets.QPushButton("Remove row")
        self.moveUpRowButton = QtWidgets.QPushButton("Move up")
        self.moveDownRowButton = QtWidgets.QPushButton("Move down")
        self.tableButtonsLayout.addWidget(self.addRowButton)
        self.tableButtonsLayout.addWidget(self.removeRowButton)
        self.tableButtonsLayout.addWidget(self.moveUpRowButton)
        self.tableButtonsLayout.addWidget(self.moveDownRowButton)
        self.tableButtonsLayout.addStretch(1)
        self.sequenceTargetsBoxLayout.addLayout(self.tableButtonsLayout)

        self.addRowButton.clicked.connect(self.add_row)
        self.removeRowButton.clicked.connect(self.remove_selected_rows)
        self.moveUpRowButton.clicked.connect(lambda: self.move_selected_row(-1))
        self.moveDownRowButton.clicked.connect(lambda: self.move_selected_row(1))
        self.refresh_target_columns()
######################################## Fraction Collector ########################################
        self.fractioncollectorBox = QtWidgets.QGroupBox("Fraction Collector")
        self.fractioncollectorBox.setMaximumHeight(400)
        self.fractioncollectorBox.setMaximumWidth(300)
        self.fractioncollectorBoxLayout = QtWidgets.QVBoxLayout(self.fractioncollectorBox)
        self.fractioncollector = fd.AzuraFC61()

        self.fractionConnectButton = QtWidgets.QPushButton("Connect Fraction Collector")
        self.fractionDisconnectButton = QtWidgets.QPushButton("Disconnect Fraction Collector")
        self.fractionMovePositionLabel = QtWidgets.QLabel("Move position")
        self.fractionMovePositionText = QtWidgets.QLineEdit("A1")
        self.fractionMoveButton = QtWidgets.QPushButton("Move to Position")
        self.fractionResetButton = QtWidgets.QPushButton("Reset (A1)")
        self.fractionNextPositionButton = QtWidgets.QPushButton("Move to Next Position")
        

        self.fractioncollectorBoxLayout.addWidget(self.fractionConnectButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionDisconnectButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMovePositionLabel)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMovePositionText)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMoveButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionResetButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionNextPositionButton)
        self.fractioncollectorBoxLayout.addStretch(1)

        self.fractionConnectButton.clicked.connect(self.connect_fraction_collector)
        self.fractionMoveButton.clicked.connect(self.move_fraction_collector)
        self.fractionResetButton.clicked.connect(self.reset_fraction_collector)
        self.fractionDisconnectButton.clicked.connect(self.disconnect_fraction_collector)
        self.fractionNextPositionButton.clicked.connect(self.move_to_next_position)

        self._layout.addWidget(self.fractioncollectorBox, 0, 1, 1, 1, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)


    def add_pump(self):
        self.pump_count += 1
        pump_widget = pw.PumpControl(self, pumpName=f"Pump {self.pump_count}")
        self.pump_widgets.append(pump_widget)
        if not hasattr(pump_widget, "_sequence_name_sync_connected"):
            pump_widget.nameEdit.textChanged.connect(self.refresh_target_columns)
            pump_widget._sequence_name_sync_connected = True

        row = (self.pump_count - 1) // self.pump_columns
        column = (self.pump_count - 1) % self.pump_columns
        self.pumpsLayout.addWidget(pump_widget, row, column, QtCore.Qt.AlignLeft)
        setattr(self, f"pump{self.pump_count}", pump_widget)
        self.refresh_target_columns()

    def add_valve(self):
        self.valve_count += 1
        valve_widget = vw.ValveControl(self, valveName=f"Valve {self.valve_count}")
        self.valve_widgets.append(valve_widget)

        row = (self.valve_count - 1) // self.valve_columns
        column = (self.valve_count - 1) % self.valve_columns
        self.valvesLayout.addWidget(valve_widget, row, column, QtCore.Qt.AlignLeft)
        setattr(self, f"valve{self.valve_count}", valve_widget)

    def resetWidgets(self):
        for pump_widget in self.pump_widgets:
            pump_widget.setParent(None)
            pump_widget.deleteLater()
        for valve_widget in self.valve_widgets:
            valve_widget.setParent(None)
            valve_widget.deleteLater()

        self.pump_widgets = []
        self.valve_widgets = []
        self.pump_count = 0
        self.valve_count = 0
        self.refresh_target_columns()

    def _get_table_headers(self):
        headers = []

        for index, pump_widget in enumerate(self.pump_widgets, start=1):
            pump_name = pump_widget.nameEdit.text().strip()
            if not pump_name:
                pump_name = f"Pump {index}"
            headers.append(f"{pump_name} target flowrate [mL/min]")

        if not headers:
            headers.append("Target flowrate (pump) [mL/min]")

        headers.append("Temperature [°C]")
        return headers

    def refresh_target_columns(self):
        old_headers = []
        for col in range(self.targetsTable.columnCount()):
            header_item = self.targetsTable.horizontalHeaderItem(col)
            old_headers.append(header_item.text() if header_item else f"Column {col}")

        old_data = []
        for row in range(self.targetsTable.rowCount()):
            row_data = {}
            for col, header in enumerate(old_headers):
                item = self.targetsTable.item(row, col)
                row_data[header] = item.text() if item else ""
            old_data.append(row_data)

        new_headers = self._get_table_headers()
        self.targetsTable.setColumnCount(len(new_headers))
        self.targetsTable.setHorizontalHeaderLabels(new_headers)

        for row in range(self.targetsTable.rowCount()):
            row_values = old_data[row] if row < len(old_data) else {}
            for col, header in enumerate(new_headers):
                value = row_values.get(header, "")
                self.targetsTable.setItem(row, col, QtWidgets.QTableWidgetItem(value))

    def add_row(self):
        row_index = self.targetsTable.rowCount()
        self.targetsTable.insertRow(row_index)
        for column_index in range(self.targetsTable.columnCount()):
            self.targetsTable.setItem(row_index, column_index, QtWidgets.QTableWidgetItem(""))

    def remove_selected_rows(self):
        selected_rows = sorted({index.row() for index in self.targetsTable.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            self.targetsTable.removeRow(row)

    def move_selected_row(self, direction):
        selected_rows = sorted({index.row() for index in self.targetsTable.selectedIndexes()})
        if not selected_rows:
            return

        current_row = selected_rows[0]
        target_row = current_row + direction

        if target_row < 0 or target_row >= self.targetsTable.rowCount():
            return

        current_values = []
        target_values = []
        for col in range(self.targetsTable.columnCount()):
            current_item = self.targetsTable.item(current_row, col)
            target_item = self.targetsTable.item(target_row, col)
            current_values.append(current_item.text() if current_item else "")
            target_values.append(target_item.text() if target_item else "")

        for col, value in enumerate(target_values):
            self.targetsTable.setItem(current_row, col, QtWidgets.QTableWidgetItem(value))
        for col, value in enumerate(current_values):
            self.targetsTable.setItem(target_row, col, QtWidgets.QTableWidgetItem(value))

        self.targetsTable.selectRow(target_row)

    def _platform_file_path(self):
        return os.path.join(os.path.dirname(__file__), "platform_layout.json")

    def _is_fraction_collector_connected(self):
        return getattr(self.fractioncollector, "sock", None) is not None

    def connect_fraction_collector(self):
        try:
            if self._is_fraction_collector_connected():
                print("Fraction collector already connected.")
                return
            self.fractioncollector.connect()
            self.fractionConnectButton.setText("Fraction Collector Connected")
            self.fractioncollector.set_remote()
        except Exception as error:
            print(f"Failed to connect fraction collector: {error}")


    def disconnect_fraction_collector(self):
        try:
            if not self._is_fraction_collector_connected():
                print("Fraction collector is not connected.")
                return
            self.fractioncollector.disconnect()
            self.fractionConnectButton.setText("Connect Fraction Collector")
        except Exception as error:
            print(f"Failed to disconnect fraction collector: {error}")


    def move_to_next_position(self):
        if not self._is_fraction_collector_connected():
            print("Connect the fraction collector first.")
            return

        try:
            self.fractioncollector.move_next()
        except Exception as error:
            print(f"Failed to move fraction collector to next position: {error}")

    def move_fraction_collector(self):
        position = self.fractionMovePositionText.text().strip().upper()
        if not position:
            print("Please enter a move position (e.g. A1).")
            return

        try:
            # Ensure we are actually connected at the network level
            # A quick 'REMOTE?' check is a good way to see if the pipe is still open
            self.fractioncollector.set_remote(timeout_ms=0) 
            
            self.fractioncollector.move_to_vial(position)
            print(f"Moved to {position}")
            
        except ConnectionError:
            print("Connection lost. Please click Connect again.")
            self.fractionConnectButton.setText("Connect Fraction Collector")
            
        except Exception as error:
            print(f"Failed to move: {error}")

            try:
                self.fractioncollector.move_to_vial(position)
            except Exception as error:
                print(f"Failed to move fraction collector to {position}: {error}")

    def reset_fraction_collector(self):
        self.fractionMovePositionText.setText("A1")
        self.move_fraction_collector()

    def _set_combo_text(self, combo, value):
        if not value:
            return
        if combo.findText(value) == -1:
            combo.addItem(value)
        combo.setCurrentText(value)

    def save_platform(self):
        pumps = []
        for pump_widget in self.pump_widgets:
            pumps.append({
                "name": pump_widget.nameEdit.text().strip(),
                "model": pump_widget.pumpModelCombo.currentText(),
                "com_port": pump_widget.comPort.currentText(),
            })

        valves = []
        for valve_widget in self.valve_widgets:
            valves.append({
                "name": valve_widget.nameEdit.text().strip(),
                "type": valve_widget.valveTypeCombo.currentText(),
                "com_port": valve_widget.comPort.currentText(),
            })

        thermocontroller = {
            "name": self.thermocontroller.nameEdit.text().strip(),
            "com_port": self.thermocontroller.comPort.currentText(),
            "target_temp": self.thermocontroller.targetTempText.text().strip(),
        }

        data = {
            "pumps": pumps,
            "valves": valves,
            "thermocontroller": thermocontroller,
        }

        with open(self._platform_file_path(), "w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=2)

    def load_platform(self):
        path = self._platform_file_path()
        if not os.path.exists(path):
            msgbox = QtWidgets.QMessageBox(self)
            msgbox.setWindowTitle("Load platform")
            msgbox.setText("No saved platform layout found.")
            msgbox.exec()
            return

        with open(path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        self.resetWidgets()

        for pump_data in data.get("pumps", []):
            self.add_pump()
            pump_widget = self.pump_widgets[-1]
            saved_name = pump_data.get("name") or pump_widget.nameEdit.text()
            pump_widget._default_name = saved_name
            pump_widget.nameEdit.setText(saved_name)
            self._set_combo_text(pump_widget.pumpModelCombo, pump_data.get("model"))
            pump_widget.formatWidget(pump_widget.pumpModelCombo.currentText())
            self._set_combo_text(pump_widget.comPort, pump_data.get("com_port"))

        for valve_data in data.get("valves", []):
            self.add_valve()
            valve_widget = self.valve_widgets[-1]
            saved_name = valve_data.get("name") or valve_widget.nameEdit.text()
            valve_widget._default_name = saved_name
            valve_widget.nameEdit.setText(saved_name)
            self._set_combo_text(valve_widget.valveTypeCombo, valve_data.get("type"))
            valve_widget.formatWidget(valve_widget.valveTypeCombo.currentText())
            self._set_combo_text(valve_widget.comPort, valve_data.get("com_port"))

        # Load thermocontroller settings
        thermocontroller_data = data.get("thermocontroller", {})
        saved_name = thermocontroller_data.get("name") or self.thermocontroller.nameEdit.text()
        self.thermocontroller._default_name = saved_name
        self.thermocontroller.nameEdit.setText(saved_name)
        self._set_combo_text(self.thermocontroller.comPort, thermocontroller_data.get("com_port"))
        target_temp = thermocontroller_data.get("target_temp", "")
        if target_temp:
            self.thermocontroller.targetTempText.setText(target_temp)

    def set_monitor_configuration(self):
        """Trigger platform monitor to load pump configuration."""
        if self.main is None or not hasattr(self.main, 'platform_monitor'):
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor not available.")
            return
        
        # Call the set_configuration method on platform_monitor
        if hasattr(self.main.platform_monitor, 'set_configuration'):
            self.main.platform_monitor.set_configuration()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor configuration method not found.")
