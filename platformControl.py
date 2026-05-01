from PyQt5 import QtWidgets, QtCore
import pumpWidget as pw
import valveWidget as vw
import thermocontrollerwidget as tcw
import fraction_driver as fd
import pandas as pd
import time
from sequence_manager import SequenceExecutor
from fraction_collector_handler import FractionCollectorHandler
from platform_config import PlatformConfigHandler
import os 
import platform_monitor
import datetime

class PlatformControl(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(PlatformControl, self).__init__(parent)

        self.fractioncollector = fd.AzuraFC61()

        self.fraction_delay_volume_ml = 0.556

        self.main = main
        # start_time_str can be sourced from Platform Monitor when available
        self.start_time_str = None
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
        self.thermocontrollerBox = QtWidgets.QGroupBox("Thermocontroller")
        self.thermocontrollerBox.setMaximumHeight(400)
        self.thermocontrollerBox.setMaximumWidth(300)
        self.thermocontrollerBoxLayout = QtWidgets.QVBoxLayout(self.thermocontrollerBox)
        self.thermocontroller = tcw.ThermocontrollerControl(self)
        self.thermocontrollerBoxLayout.addWidget(self.thermocontroller)
        self._layout.addWidget(self.thermocontrollerBox, 0, 2, 1, 1, QtCore.Qt.AlignTop | QtCore.Qt.AlignRight)

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
        self.stopSequenceButton = QtWidgets.QPushButton("Stop Sequence")
        self.tableButtonsLayout.addWidget(self.addRowButton)
        self.tableButtonsLayout.addWidget(self.removeRowButton)
        self.tableButtonsLayout.addWidget(self.moveUpRowButton)
        self.tableButtonsLayout.addWidget(self.moveDownRowButton)
        self.tableButtonsLayout.addWidget(self.runSequenceButton)
        self.tableButtonsLayout.addWidget(self.stopSequenceButton)
        self.tableButtonsLayout.addStretch(1)
        self.sequenceTargetsBoxLayout.addLayout(self.tableButtonsLayout)

        self.addRowButton.clicked.connect(self.add_row)
        self.removeRowButton.clicked.connect(self.remove_selected_rows)
        self.moveUpRowButton.clicked.connect(lambda: self.move_selected_row(-1))
        self.moveDownRowButton.clicked.connect(lambda: self.move_selected_row(1))
        self.runSequenceButton.clicked.connect(self.run_sequence)
        self.stopSequenceButton.clicked.connect(self.stop_sequence)
        self.refresh_target_columns()
        self.sequence_targets_df = self.get_sequence_targets_df()
        self.targetsTable.itemChanged.connect(self._on_targets_table_changed)
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
        self.fractionResetButton = QtWidgets.QPushButton("Reset (HOME)")
        self.fractionNextPositionButton = QtWidgets.QPushButton("Move to Next Position")

        self.sampleVolumeLabel = QtWidgets.QLabel("Sample Volume (ml)")
        self.sampleVolumeText = QtWidgets.QLineEdit("0.5")
        self.sample_volume = 0.5
        self.sample_duration = 0.0

        self.sample_count = 1
        self.sampleCountLabel = QtWidgets.QLabel("Sample count")
        self.sampleCountText = QtWidgets.QLineEdit("1")

        self.reactor_volume_ml = 2
        self.reactorVolumeLabel = QtWidgets.QLabel("Reactor Volume (ml)")
        self.reactorVolumeText = QtWidgets.QLineEdit("2")
        
    
        self.fraction_delay_volume_ml = 0.556
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

        self._sequence_running = False
        self._sequence_callback_token = 0
        self._sequence_timers = []
        self.sequence_executor = SequenceExecutor(self)
        self.fraction_handler = FractionCollectorHandler(self)
        self.config_handler = PlatformConfigHandler(self)


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
        headers.append("Fraction Collector Position")
        return headers

    def _get_monitor_start_time_str(self):
        """Return the start_time_str from the Platform Monitor when available.

        Falls back to a locally cached `self.start_time_str` or generates a new
        timestamp if none exists.
        """
        # Prefer monitor value if accessible
        try:
            if self.main is not None and hasattr(self.main, 'platform_monitor'):
                pm = self.main.platform_monitor
                if pm is not None and hasattr(pm, 'start_time_str') and pm.start_time_str:
                    return pm.start_time_str
        except Exception:
            pass

        # Fallback: use existing local value or create one
        if getattr(self, 'start_time_str', None):
            return self.start_time_str

        self.start_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self.start_time_str

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
            row_data = {}
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
        return self.config_handler._platform_file_path()

    def _is_fraction_collector_connected(self):
        return self.fraction_handler._is_fraction_collector_connected()

    def connect_fraction_collector(self):
        return self.fraction_handler.connect_fraction_collector()

    def _retry_fraction_collector_command(self, command_name, command_callback):
        return self.fraction_handler._retry_fraction_collector_command(command_name, command_callback)

    def disconnect_fraction_collector(self):
        return self.fraction_handler.disconnect_fraction_collector()

    def move_to_next_position(self):
        return self.fraction_handler.move_to_next_position()

    def move_fraction_collector(self):
        return self.fraction_handler.move_fraction_collector()

    def reset_fraction_collector(self):
        return self.fraction_handler.reset_fraction_collector()

    def _set_combo_text(self, combo, value):
        if not value:
            return
        if combo.findText(value) == -1:
            combo.addItem(value)
        combo.setCurrentText(value)

    def _invalidate_sequence_callbacks(self):
        self._sequence_callback_token += 1

    def _cancel_sequence_timers(self):
        for timer in list(self._sequence_timers):
            try:
                timer.stop()
                timer.deleteLater()
            except Exception:
                pass
        self._sequence_timers.clear()

    def _schedule_sequence_timer(self, delay_ms, callback):
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        expected_token = self._sequence_callback_token

        def _on_timeout(timer_obj=timer, token=expected_token, cb=callback):
            if timer_obj in self._sequence_timers:
                self._sequence_timers.remove(timer_obj)
            timer_obj.deleteLater()

            if not self._sequence_running:
                return
            if token != self._sequence_callback_token:
                return

            cb()

        timer.timeout.connect(_on_timeout)
        self._sequence_timers.append(timer)
        timer.start(max(0, int(delay_ms)))
        return timer

    def _schedule_timer(self, delay_ms, callback, track_sequence=False):
        if track_sequence:
            return self._schedule_sequence_timer(delay_ms, callback)
        QtCore.QTimer.singleShot(max(0, int(delay_ms)), callback)
        return None

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
        return self.config_handler.save_platform()

    def load_platform(self):
        return self.config_handler.load_platform()

########### Methods for running sequences and controlling fractioncollector ###########
    def set_monitor_configuration(self):
        if self.main is None or not hasattr(self.main, 'platform_monitor'):
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor not available.")
            return

        if hasattr(self.main.platform_monitor, 'set_configuration'):
            self.main.platform_monitor.set_configuration()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Platform Monitor configuration method not found.")


    def temp_reached(self, temperature):
        try:
            target_temp_str = self.thermocontroller.targetTempText.text().strip()
            if not target_temp_str:
                return False
            target_temp = float(target_temp_str)
        except (ValueError, AttributeError):
            return False
        
        try:
            current_temp = float(temperature)
        except (ValueError, TypeError):
            return False
        
        return current_temp == target_temp
    
    def fractioncollector_sample(self, sample_id, on_complete=None, track_sequence_timer=False):
        return self.fraction_handler.fractioncollector_sample(sample_id, on_complete, track_sequence_timer)

    def _start_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None, track_sequence_timer=False):
        return self.fraction_handler._start_fractioncollector_collection(sample_id, total_flow_ml_min, on_complete, track_sequence_timer)

    def _finish_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None):
        return self.fraction_handler._finish_fractioncollector_collection(sample_id, total_flow_ml_min, on_complete)

    def _apply_row_flowrates(self, row_data):
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

    def run_sequence(self):
        return self.sequence_executor.run_sequence()

    def stop_sequence(self):
        """Stop the running sequence, set all pumps to 0.1 mL/min, reset the auto sampler, set temperature to 25.0 C."""
        # Stop the sequence
        self._sequence_running = False
        self._invalidate_sequence_callbacks()
        self._cancel_sequence_timers()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence stopped.")





        log_dir = "Sequence_logs"
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        start_time_for_log = self._get_monitor_start_time_str()
        log_path = os.path.join(log_dir, f"Sequence_log_{start_time_for_log}.csv")
        try:
            self._sequence_df.to_csv(log_path, index=False)
            print(f"[{time.strftime('%H:%M:%S')}] Sequence log saved to {log_path}")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to save sequence log: {error}")

        # Set temperature to 25.0 C
        try:
            self.thermocontroller.targetTempText.setText("25.0")
            self.thermocontroller.setTargetTemperature()
            print(f"[{time.strftime('%H:%M:%S')}] Temperature set to 25.0 C.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to set temperature: {error}")


        # Set all pumps to 0.1 mL/min and stop them
        for pump_widget in self.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"):
                continue

            try:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                pump_widget.setFlowrateText.setText("0.1")
                pump_widget.setFlowrate()
                pump_widget.stop()
                print(f"[{time.strftime('%H:%M:%S')}] {pump_name} stopped at 0.1 mL/min.")
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"[{time.strftime('%H:%M:%S')}] Failed to stop {pump_name}: {error}")

        # Reset the fraction collector to HOME
        try:
            if self._is_fraction_collector_connected():
                self.reset_fraction_collector()
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector reset to HOME.")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector not connected.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to reset fraction collector: {error}")
    
        
        print(f"[{time.strftime('%H:%M:%S')}] Sequence stop complete.")
