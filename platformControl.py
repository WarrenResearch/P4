import json
import os
from PyQt5 import QtWidgets, QtCore
import pumpWidget as pw
import valveWidget as vw
import thermocontrollerwidget as tcw
import fraction_driver as fd
import pandas as pd
import time

### Class used to define all apparatus available for automated experiments ###

# All pumps and valves are controlled from other scripts by calling to the same instance of the PlatformControl class created in the GUI initialisation.

class PlatformControl(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(PlatformControl, self).__init__(parent)

        self.fractioncollector = fd.AzuraFC61() # single Azura device used for both fraction collection and sampling

        
        self.fraction_delay_volume_ml = 0.556 # volume between reactor and fraction collector outlet 

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
        self._layout.addWidget(self.sequenceTargetsBox, 1, 1, 1, 2)

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
        self.runSequenceButton = QtWidgets.QPushButton("Run Sequence")
        self.tableButtonsLayout.addWidget(self.addRowButton)
        self.tableButtonsLayout.addWidget(self.removeRowButton)
        self.tableButtonsLayout.addWidget(self.moveUpRowButton)
        self.tableButtonsLayout.addWidget(self.moveDownRowButton)
        self.tableButtonsLayout.addWidget(self.runSequenceButton)
        self.tableButtonsLayout.addStretch(1)
        self.sequenceTargetsBoxLayout.addLayout(self.tableButtonsLayout)

        self.addRowButton.clicked.connect(self.add_row)
        self.removeRowButton.clicked.connect(self.remove_selected_rows)
        self.moveUpRowButton.clicked.connect(lambda: self.move_selected_row(-1))
        self.moveDownRowButton.clicked.connect(lambda: self.move_selected_row(1))
        self.runSequenceButton.clicked.connect(self.run_sequence)
        self.refresh_target_columns()
        self.sequence_targets_df = self.get_sequence_targets_df()
        self.targetsTable.itemChanged.connect(self._on_targets_table_changed)
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

        self.sampleVolumeLabel = QtWidgets.QLabel("Sample Volume (ml)")
        self.sampleVolumeText = QtWidgets.QLineEdit("0.5")
        self.sample_volume = 0.5 # default sample volume in mL, used if user input is invalid. Updated whenever user edits sample volume text field and valid value is entered.
        self.sample_duration = 0.0 
        
        self.sample_count = 1 #number of samples to be taken
        self.sampleCountLabel = QtWidgets.QLabel("Sample count")
        self.sampleCountText = QtWidgets.QLineEdit("1")

        self.reactor_volume_ml = 2 # default reactor volume in mL
        self.reactorVolumeLabel = QtWidgets.QLabel("Reactor Volume (ml)")
        self.reactorVolumeText = QtWidgets.QLineEdit("2")
        
    
        self.fraction_delay_volume_ml = 0.556 # starting delay volume
        self.fractionDelayVolumeLabel = QtWidgets.QLabel("Delay Volume (ml)")
        self.fractionDelayVolumeText = QtWidgets.QLineEdit("0.556")
        

        self.fractioncollectorBoxLayout.addWidget(self.fractionConnectButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionDisconnectButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMovePositionLabel)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMovePositionText)
        self.fractioncollectorBoxLayout.addWidget(self.fractionMoveButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionResetButton)
        self.fractioncollectorBoxLayout.addWidget(self.fractionNextPositionButton)
        self.fractioncollectorBoxLayout.addWidget(self.sampleVolumeLabel)
        self.fractioncollectorBoxLayout.addWidget(self.sampleVolumeText)
        self.fractioncollectorBoxLayout.addWidget(self.sampleCountLabel)
        self.fractioncollectorBoxLayout.addWidget(self.sampleCountText)
        self.fractioncollectorBoxLayout.addWidget(self.reactorVolumeLabel)
        self.fractioncollectorBoxLayout.addWidget(self.reactorVolumeText)
        self.fractioncollectorBoxLayout.addWidget(self.fractionDelayVolumeLabel)
        self.fractioncollectorBoxLayout.addWidget(self.fractionDelayVolumeText)
        self.fractioncollectorBoxLayout.addStretch(1)



        self.fractionConnectButton.clicked.connect(self.connect_fraction_collector)
        self.fractionMoveButton.clicked.connect(self.move_fraction_collector)
        self.fractionResetButton.clicked.connect(self.reset_fraction_collector)
        self.fractionDisconnectButton.clicked.connect(self.disconnect_fraction_collector)
        self.fractionNextPositionButton.clicked.connect(self.move_to_next_position)
        self.sampleVolumeText.editingFinished.connect(self.update_sample_volume)
        self.sampleCountText.editingFinished.connect(self.update_sample_count)
        self.reactorVolumeText.editingFinished.connect(self.update_reactor_volume)
        self.fractionDelayVolumeText.editingFinished.connect(self.update_fraction_delay_volume)

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
            headers.append(f"{pump_name} [mL/min]")

        if not headers:
            headers.append("(pump) [mL/min]")

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

    def get_sequence_targets_df(self):
        """Return Reactor Sequence table rows as a pandas DataFrame."""

        headers = []
        for col in range(self.targetsTable.columnCount()):
            header_item = self.targetsTable.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item else f"Column {col}")

        rows = []
        for row in range(self.targetsTable.rowCount()):
            row_data = {} # Use a dict to ensure we can handle changes in column order or count without losing data integrity
            for col, header in enumerate(headers):
                item = self.targetsTable.item(row, col)
                row_data[header] = item.text() if item else ""
            rows.append(row_data)

        return pd.DataFrame(rows, columns=headers)

    def upload_sequence(self):
        """Update the cached sequence DataFrame from current table contents."""
        self.sequence_targets_df = self.get_sequence_targets_df()
        return self.sequence_targets_df

    def _on_targets_table_changed(self, _item):
        self.upload_sequence()

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
                return True
            self.fractioncollector.connect()
            self.fractionConnectButton.setText("Fraction Collector Connected")
            self.fractioncollector.set_remote(timeout_ms=0) # Set remote mode with no timeout to keep connection alive until explicitly disconnected
            return True
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to connect fraction collector: {error}")
            return False

    def _retry_fraction_collector_command(self, command_name, command_callback):
        try:
            return command_callback()
        except ConnectionError as error:
            print(f"[{time.strftime('%H:%M:%S')}] Fraction collector connection lost during {command_name}: {error}")
            if not self.connect_fraction_collector():
                return False

            try:
                return command_callback()
            except Exception as retry_error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to {command_name} after reconnect: {retry_error}")
                return False


    def disconnect_fraction_collector(self):
        try:
            if not self._is_fraction_collector_connected():
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector is not connected.")
                return
            self.fractioncollector.disconnect()
            self.fractionConnectButton.setText("Connect Fraction Collector")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to disconnect fraction collector: {error}")


    def move_to_next_position(self):
        if not self._is_fraction_collector_connected():
            print(f"[{time.strftime('%H:%M:%S')}] Connect the fraction collector first.")
            return

        try:
            self.fractioncollector.move_next()
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to next position: {error}")

    def move_fraction_collector(self):
        position = self.fractionMovePositionText.text().strip().upper()
        if not position:
            print(f"[{time.strftime('%H:%M:%S')}] Please enter a move position (e.g. A1).")
            return

        try:
            # Ensure we are actually connected at the network level
            # A quick 'REMOTE?' check is a good way to see if the pipe is still open
            self.fractioncollector.set_remote(timeout_ms=0) 
            
            self.fractioncollector.move_to_vial(position)
            print(f"[{time.strftime('%H:%M:%S')}] Moved to {position}")
            
        except ConnectionError:
            print(f"[{time.strftime('%H:%M:%S')}] Connection lost. Please click Connect again.")
            self.fractionConnectButton.setText("Connect Fraction Collector")
            
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to move: {error}")

            try:
                self.fractioncollector.move_to_vial(position)
            except Exception as error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to {position}: {error}")

    def reset_fraction_collector(self):
        self.fractionMovePositionText.setText("A1")
        self.move_fraction_collector()

    def _set_combo_text(self, combo, value):
        if not value:
            return
        if combo.findText(value) == -1:
            combo.addItem(value)
        combo.setCurrentText(value)

    def update_sample_volume(self):
        value_text = self.sampleVolumeText.text().strip()
        try:
            value = float(value_text)
            if value <= 0:
                raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Sample volume", "Enter a positive number of milliliters.")
            self.sampleVolumeText.setText(str(self.sample_volume))
            return False

        self.sample_volume = value
        return True

    def update_sample_count(self):
        value_text = self.sampleCountText.text().strip()
        try:
            value = int(value_text)
            if value <= 0:
                raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Sample count", "Enter a positive whole number of samples.")
            self.sampleCountText.setText(str(self.sample_count))
            return False

        self.sample_count = value
        return True

    def update_reactor_volume(self):
        value_text = self.reactorVolumeText.text().strip()
        try:
            value = float(value_text)
            if value <= 0:
                raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Reactor volume", "Enter a positive number of milliliters.")
            self.reactorVolumeText.setText(str(self.reactor_volume_ml))
            return False

        self.reactor_volume_ml = value
        return True

    def update_fraction_delay_volume(self):
        value_text = self.fractionDelayVolumeText.text().strip()
        try:
            value = float(value_text)
            if value < 0:
                raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Delay volume", "Enter a non-negative number of milliliters.")
            self.fractionDelayVolumeText.setText(str(self.fraction_delay_volume_ml))
            return False

        self.fraction_delay_volume_ml = value
        return True

    def _get_total_current_flowrate_ml_min(self): #cycles through the pump widgets and sums the current flowrate values to calculate total flowrate in mL/min for use in sample duration calculation
        total_flow_ml_min = 0.0
        for pump_widget in self.pump_widgets:
            if not hasattr(pump_widget, "setFlowrateText"):
                continue

            flow_text = pump_widget.setFlowrateText.text().strip()
            if not flow_text:
                continue

            try:
                flow_value = float(flow_text)
            except ValueError:
                continue

            if flow_value > 0:
                total_flow_ml_min += flow_value

        return total_flow_ml_min

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
            "reactor_volume_ml": self.reactor_volume_ml,
            "fraction_delay_volume_ml": self.fraction_delay_volume_ml,
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

        reactor_volume = data.get("reactor_volume_ml", self.reactor_volume_ml)
        try:
            reactor_volume = float(reactor_volume)
            if reactor_volume <= 0:
                raise ValueError
        except (TypeError, ValueError):
            reactor_volume = self.reactor_volume_ml

        self.reactor_volume_ml = reactor_volume
        self.reactorVolumeText.setText(str(reactor_volume))

        fraction_delay_volume = data.get("fraction_delay_volume_ml", self.fraction_delay_volume_ml)
        try:
            fraction_delay_volume = float(fraction_delay_volume)
            if fraction_delay_volume < 0:
                raise ValueError
        except (TypeError, ValueError):
            fraction_delay_volume = self.fraction_delay_volume_ml

        self.fraction_delay_volume_ml = fraction_delay_volume
        self.fractionDelayVolumeText.setText(str(fraction_delay_volume))

########### Methods for running sequences and controlling fractioncollector ###########
    def set_monitor_configuration(self):
        """Trigger platform monitor to load pump configuration."""
        if self.main is None or not hasattr(self.main, 'platform_monitor'): #if the window cant be found, throw an error message and return
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor not available.")
            return #returns early to avoid calling method on non-existent monitor
        
        # Call the set_configuration method on platform_monitor
        if hasattr(self.main.platform_monitor, 'set_configuration'): #if the method exists, call it to update the monitor configuration based on current pumps
            self.main.platform_monitor.set_configuration()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor configuration method not found.")


    def temp_reached(self, temperature):
        """Check if target temperature is reached.
        
        Args:
            temperature: Current temperature reading.
            
        Returns:
            True if target temperature equals current temperature, False otherwise.
        """
        try:
            target_temp_str = self.thermocontroller.targetTempText.text().strip() # get the target temperature from the thermocontroller widget as a string
            if not target_temp_str:
                return False
            target_temp = float(target_temp_str) #convert the string into a float (new variable target_temp) for comparison with current temperature
        except (ValueError, AttributeError): # except if an error is thrown
            return False
        
        try:
            current_temp = float(temperature) # convert the input temperature (current temperature reading) into a float for comparison with target temperature
        except (ValueError, TypeError):
            return False
        
        return current_temp == target_temp # return True if current temperature equals target temperature, otherwise return False to indicate target has not been reached yet
    
    def wash_step(self, on_complete=None): # runs solution through at 1 mol min
        wash_flowrate_ml_min = 1.0 
        wash_volume_ml = 1.5 * float(self.reactor_volume_ml)
        wash_duration_s = (wash_volume_ml / wash_flowrate_ml_min) * 60.0
        wash_duration_min = wash_duration_s / 60.0
        wash_duration_ms = int(wash_duration_s * 1000) # for qtimer.singleshot

        active_pumps = [] #list of active pumps 
        for pump_widget in self.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"): #if the widget doesnt have pumpobj (i.e. not properly configured), skip it and move to the next pump widget
                continue

            try:
                pump_widget.setFlowrateText.setText(str(wash_flowrate_ml_min)) # set the flowrate text field to the wash flowrate value (1 mL/min)
                pump_widget.setFlowrate()
                pump_widget.start()
                active_pumps.append(pump_widget) # add the pump widget to the list of active pumps that will be stopped after the wash duration elapses
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Wash step skipped for {pump_name}: {error}")

        if not active_pumps: #if there are no pumps throw this error message
            print("Wash step aborted: no connected pumps available.")
            return False 

        print(
            f"Wash step running at {wash_flowrate_ml_min} mL/min for {wash_volume_ml:.2f} mL "
            f"({wash_duration_min:.1f} min)."
        )
        #after wash duration has elapsed, call _finish_wash_step 
        QtCore.QTimer.singleShot( 
            wash_duration_ms,
            lambda pumps=active_pumps, callback=on_complete: self._finish_wash_step(pumps, callback),
        )
        return True


    def _finish_wash_step(self, active_pumps, on_complete=None): #gets the active pumps, sets them to 0.01 ml min
        for pump_widget in active_pumps:
            try:
                pump_widget.setFlowrateText.setText('0.01')
                pump_widget.setFlowrate()
                pump_widget.start()
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Failed to stop {pump_name} after wash step: {error}")

        print("Wash step complete.")
        if callable(on_complete):
            on_complete()



    def fractioncollector_sample(self, sample_id, on_complete=None):
        """Trigger fraction collector to take a sample and mark the sample point in platform monitor.
        
        Args:
            sample_id: Identifier for the sample (e.g., vial number, timestamp).
        """

        if not self.update_sample_volume(): # validate and update sample volume from user input before proceeding. If invalid, show error message and abort sampling.
            return False
        
        total_flow_ml_min = self._get_total_current_flowrate_ml_min() # get total flowrate from all pumps to calculate sample duration based on sample volume. If total flowrate is 0, show error message and abort sampling to avoid division by zero.
        if total_flow_ml_min <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Sample duration",
                "Cannot calculate sample duration: total flowrate must be greater than 0 mL/min.",
            )
            return False
        
        self.sample_duration = (self.sample_volume / total_flow_ml_min) * 60.0 #get sample duration
        print(
            f"Sample duration calculated from volume/flowrate: "
            f"{self.sample_volume:.3f} mL / {total_flow_ml_min:.3f} mL/min = {self.sample_duration:.1f} s"
        )

        if not self.connect_fraction_collector(): #failed to connect, show error message and abort sampling
            return False

        if not self._retry_fraction_collector_command( #tries the retry method incase connection drops for some reason, if it still fails after retrying, show error message and abort sampling
            "move fraction collector to next vial",
            lambda: self.fractioncollector.move_next(collect_mode=0),
        ):
            return False

        QtCore.QTimer.singleShot( #schedules the collection to start after 1 second
            1000,
            lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete: self._start_fractioncollector_collection(sid, flow, callback),
        )
        return True

    def _start_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None): #called after 1 second delay from fractioncollector_sample, starts the sample collection and schedules the stop collection after the calculated sample duration has elapsed
        if not self.connect_fraction_collector():
            if callable(on_complete):
                on_complete() # check if on_complete is a callable function before calling it to avoid errors, then return to abort sampling since we failed to connect to the fraction collector
            return

        if not self._retry_fraction_collector_command(
            "start sample collection",
            lambda: self.fractioncollector.set_collect(1),
        ):
            if callable(on_complete):
                on_complete()
            return

        print(f"Starting sample collection for {self.sample_duration:.1f} s.")

        duration_ms = max(0, int(self.sample_duration * 1000)) #after a delay of the sample duration, send a signal to stop sample collection
        QtCore.QTimer.singleShot(
            duration_ms,
            lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete: self._finish_fractioncollector_collection(sid, flow, callback),
        )

    def _finish_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None):
        if not self.connect_fraction_collector():
            if callable(on_complete):
                on_complete()
            return

        if not self._retry_fraction_collector_command(
            "stop sample collection",
            lambda: self.fractioncollector.set_collect(0),
        ):
            print("Failed to stop sample collection.")
        else:
            print(f"Sample taken: {sample_id}")

        if self.main is not None and hasattr(self.main, "platform_monitor"): # stamp the sample event on platform monitor 
            event_text = (
                f"SAMPLE_TAKEN;id={sample_id};"
                f"volume_ml={self.sample_volume:.3f}"
            )
            try:
                self.main.platform_monitor.continuous_log_function(event=event_text)
            except Exception as error:
                print(f"Failed to log sample event in platform monitor: {error}")

        if callable(on_complete):
            on_complete()

    def _apply_row_flowrates(self, row_data): #set flowrates for each pump based on the row  (flow_column) values
        total_flow_ml_min = 0.0
        for pump_widget in self.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"):
                continue

            pump_name = pump_widget.nameEdit.text().strip()
            if not pump_name:
                continue

            flow_column = f"{pump_name} [mL/min]"
            if flow_column not in row_data:
                continue

            flow_value = row_data.get(flow_column)
            if pd.isna(flow_value) or str(flow_value).strip() == "":
                continue

            try:
                flow_float = float(flow_value)
                pump_widget.setFlowrateText.setText(str(flow_float))
                pump_widget.setFlowrate()
                pump_widget.start()
                total_flow_ml_min += flow_float
            except Exception as error:
                print(f"Failed to set row flowrate for {pump_name}: {error}")

        return total_flow_ml_min

    def _poll_temp_and_handle_row(self): #checks if we have reached target temperature yet, if not, waits 2 seconds and checks again
        current_temp_text = self.thermocontroller.currentTempDisplay.text().strip()
        if not self.temp_reached(current_temp_text):
            QtCore.QTimer.singleShot(2000, self._poll_temp_and_handle_row)
            return

        print("Target temperature reached. Starting wash step.") #once reached, start wash step
        self.wash_step(on_complete=self._on_wash_complete_for_row)

    def _on_wash_complete_for_row(self):
        row_data = getattr(self, "_active_sequence_row_data", None) #get active row data
        if not isinstance(row_data, dict):
            print("No active sequence row found after wash step.")
            return

        total_flow_ml_min = self._apply_row_flowrates(row_data)
        if total_flow_ml_min <= 0:
            print("No valid flowrates in active row; advancing to next row.")
            self._on_row_complete()
            return

        hold_volume_ml = (3.0 * float(self.reactor_volume_ml)) + self.fraction_delay_volume_ml
        hold_duration_s = (hold_volume_ml / total_flow_ml_min) * 60.0
        hold_duration_ms = int(hold_duration_s * 1000)

        print(
            f"Row hold started at total flow {total_flow_ml_min:.3f} mL/min for "
            f"{hold_volume_ml:.2f} mL ({hold_duration_s:.1f} s) (reactor volume x3 + delay volume included)."
        )
        QtCore.QTimer.singleShot(hold_duration_ms, self._on_row_complete)

    def _on_row_complete(self):
        current_row = getattr(self, "_sequence_row_index", 0)
        self._sample_current_row(current_row, 1)

    def _sample_current_row(self, current_row, sample_number): #handles the sample collection for the current row, if sample count is greater than 1, it will call itself recursively until all samples for the current row are collected before advancing to the next row
        if not self.update_sample_count():
            self._advance_sequence_after_sample(current_row)
            return

        sample_id = f"row-{current_row + 1}-sample-{sample_number}"
        started = self.fractioncollector_sample(
            sample_id,
            on_complete=lambda row=current_row, sample=sample_number: self._after_row_sample(row, sample),
        )
        if not started:
            self._advance_sequence_after_sample(current_row)

    def _after_row_sample(self, current_row, sample_number): # if we have more samples to take for the current row, call _sample_current_row again with the next sample number, otherwise advance to the next row   
        if sample_number < self.sample_count:
            self._sample_current_row(current_row, sample_number + 1)
            return

        self._advance_sequence_after_sample(current_row)

    def _advance_sequence_after_sample(self, current_row): #after sample collection is triggered for the current row, advance to the next row and start the process again. If we have reached the end of the sequence, stop running.
        self._sequence_row_index = current_row + 1
        if self._sequence_row_index >= len(self._sequence_df):
            print(f"[{time.strftime('%H:%M:%S')}] Sequence complete.")
            self._sequence_running = False
            return

        self._run_current_row()

    def _run_current_row(self): # set target temp, wait for temp reached, start wash step, set flowrates, wait for 3 reactor volumes to elapse, sample, then move to next row and repeat
        if not getattr(self, "_sequence_running", False):
            return

        if self._sequence_row_index >= len(self._sequence_df):
            print(f"[{time.strftime('%H:%M:%S')}] Sequence complete.")
            self._sequence_running = False
            return

        row_data = self._sequence_df.iloc[self._sequence_row_index].to_dict()
        self._active_sequence_row_data = row_data

        # Set flowrate to 0.01 mL/min for all connected pumps while waiting for temperature.
        for pump_widget in self.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"):
                continue

            try:
                pump_widget.setFlowrateText.setText("0.01")
                pump_widget.setFlowrate()
                pump_widget.start()
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"{pump_name}: {error}")

        temp_columns = [column for column in self._sequence_df.columns if "Temperature" in column]
        next_temp = row_data.get(temp_columns[0], "") if temp_columns else ""
        if pd.isna(next_temp) or str(next_temp).strip() == "":
            print(f"No temperature value in reactor_sequence row {self._sequence_row_index + 1}.")
            self._on_row_complete()
            return

        self.thermocontroller.targetTempText.setText(str(next_temp).strip())
        self.thermocontroller.setTargetTemperature()
        print(f"[{time.strftime('%H:%M:%S')}] Row {self._sequence_row_index + 1}: target temperature set to {next_temp} C.")

        self._poll_temp_and_handle_row()



    def run_sequence(self): 
        """Run full sequence non-blocking, row-by-row."""
        self._sequence_df = self.get_sequence_targets_df() # extract df from table 
        if self._sequence_df.empty:
            print(f"[{time.strftime('%H:%M:%S')}] reactor_sequence is empty.")
            return False

        temp_columns = [column for column in self._sequence_df.columns if "Temperature" in column]
        if not temp_columns:
            print("No temperature column found in reactor_sequence.")
            return False

        self._sequence_row_index = 0
        self._sequence_running = True
        self._run_current_row()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence started.")
        return True
