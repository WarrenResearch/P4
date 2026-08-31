import json
import os
from PyQt5.QtWidgets import QMessageBox


class PlatformConfigHandler:
    # This class saves and loads the platform layout settings.
    # It keeps file handling out of the main GUI class.
    def __init__(self, controller):
        # Keep a reference to the main platform controller.
        self.controller = controller

    def _platform_file_path(self):
        # Build the path to the JSON file used for saving the platform layout.
        return os.path.join(os.path.dirname(__file__), "platform_layout.json")

    def save_platform(self):
        # Ensure the visible table values are synced back into the in-memory list before saving.
        if hasattr(self.controller, "_sync_sample_definitions_from_table"):
            self.controller._sync_sample_definitions_from_table()

        # Collect the current settings from every pump widget.
        pumps = []
        for pump_widget in self.controller.pump_widgets:
            pumps.append({
                "name": pump_widget.nameEdit.text().strip(),
                "model": pump_widget.pumpModelCombo.currentText(),
                "com_port": pump_widget.comPort.currentText(),
                "calibration_factor": pump_widget.calibrationFactorText.text().strip() if hasattr(pump_widget, "calibrationFactorText") else "1",
            })

        # Collect the current settings from every valve widget.
        valves = []
        for valve_widget in self.controller.valve_widgets:
            valves.append({
                "name": valve_widget.nameEdit.text().strip(),
                "type": valve_widget.valveTypeCombo.currentText(),
                "com_port": valve_widget.comPort.currentText(),
            })

        # Collect thermocontroller settings.
        thermocontroller = {
            "name": self.controller.thermocontroller.nameEdit.text().strip(),
            "com_port": self.controller.thermocontroller.comPort.currentText(),
            "target_temp": self.controller.thermocontroller.targetTempText.text().strip(),
        }

        # Put all settings into one dictionary so they can be written to disk.
        data = {
            "pumps": pumps,
            "valves": valves,
            "thermocontroller": thermocontroller,
            "reactor_volume_ml": self.controller.reactor_volume_ml,
            "fraction_delay_volume_ml": self.controller.fraction_delay_volume_ml,
            "sample_definitions": list(getattr(self.controller, "sample_definitions", [])),
            "sample_name": getattr(self.controller, "sample_name", ""),
            "sample_volume": getattr(self.controller, "sample_volume", 0.5),
            "sample_count": getattr(self.controller, "sample_count", 1),
        }

        # Save the dictionary to the JSON file.
        with open(self._platform_file_path(), "w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=2)

    def load_platform(self):
        # Find the saved platform file.
        path = self._platform_file_path()

        # If there is no file yet, show a message and stop.
        if not os.path.exists(path):
            msgbox = QMessageBox(self.controller)
            msgbox.setWindowTitle("Load platform")
            msgbox.setText("No saved platform layout found.")
            msgbox.exec()
            return

        # Read the saved JSON data back into memory.
        with open(path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        # Clear the current widgets so we can rebuild from saved data.
        self.controller.resetWidgets()

        # Recreate pumps from saved settings one by one.
        for pump_data in data.get("pumps", []):
            self.controller.add_pump()
            pump_widget = self.controller.pump_widgets[-1]
            saved_name = pump_data.get("name") or pump_widget.nameEdit.text()
            pump_widget._default_name = saved_name
            pump_widget.nameEdit.setText(saved_name)
            self.controller._set_combo_text(pump_widget.pumpModelCombo, pump_data.get("model"))
            pump_widget.formatWidget(pump_widget.pumpModelCombo.currentText())
            self.controller._set_combo_text(pump_widget.comPort, pump_data.get("com_port"))
            if hasattr(pump_widget, "calibrationFactorText"):
                pump_widget.calibrationFactorText.setText(str(pump_data.get("calibration_factor", "1") or "1"))

        # Recreate valves from saved settings one by one.
        for valve_data in data.get("valves", []):
            self.controller.add_valve()
            valve_widget = self.controller.valve_widgets[-1]
            saved_name = valve_data.get("name") or valve_widget.nameEdit.text()
            valve_widget._default_name = saved_name
            valve_widget.nameEdit.setText(saved_name)
            self.controller._set_combo_text(valve_widget.valveTypeCombo, valve_data.get("type"))
            valve_widget.formatWidget(valve_widget.valveTypeCombo.currentText())
            self.controller._set_combo_text(valve_widget.comPort, valve_data.get("com_port"))

        # Restore thermocontroller settings.
        thermocontroller_data = data.get("thermocontroller", {})
        saved_name = thermocontroller_data.get("name") or self.controller.thermocontroller.nameEdit.text()
        self.controller.thermocontroller._default_name = saved_name
        self.controller.thermocontroller.nameEdit.setText(saved_name)
        self.controller._set_combo_text(self.controller.thermocontroller.comPort, thermocontroller_data.get("com_port"))
        target_temp = thermocontroller_data.get("target_temp", "")
        if target_temp:
            self.controller.thermocontroller.targetTempText.setText(target_temp)

        # Restore reactor volume, but fall back to the current value if saved data is invalid.
        reactor_volume = data.get("reactor_volume_ml", self.controller.reactor_volume_ml)
        try:
            reactor_volume = float(reactor_volume)
            if reactor_volume <= 0:
                raise ValueError
        except (TypeError, ValueError):
            reactor_volume = self.controller.reactor_volume_ml

        self.controller.reactor_volume_ml = reactor_volume
        self.controller.reactorVolumeText.setText(str(reactor_volume))

        # Restore delay volume, but fall back to the current value if saved data is invalid.
        fraction_delay_volume = data.get("fraction_delay_volume_ml", self.controller.fraction_delay_volume_ml)
        try:
            fraction_delay_volume = float(fraction_delay_volume)
            if fraction_delay_volume < 0:
                raise ValueError
        except (TypeError, ValueError):
            fraction_delay_volume = self.controller.fraction_delay_volume_ml

        self.controller.fraction_delay_volume_ml = fraction_delay_volume
        self.controller.fractionDelayVolumeText.setText(str(fraction_delay_volume))

        # Restore sample definitions list, if present.
        sample_definitions = data.get("sample_definitions")
        if isinstance(sample_definitions, list) and sample_definitions:
            self.controller.sample_definitions = []
            for item in sample_definitions:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "Sample")).strip() or "Sample"
                try:
                    volume = float(item.get("volume", self.controller.sample_volume))
                    if volume <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    volume = self.controller.sample_volume
                try:
                    count = int(item.get("count", self.controller.sample_count))
                    if count <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    count = self.controller.sample_count
                self.controller.sample_definitions.append({"name": name, "volume": volume, "count": count})
            if self.controller.sample_definitions:
                first = self.controller.sample_definitions[0]
                self.controller.sample_name = first["name"]
                self.controller.sample_volume = first["volume"]
                self.controller.sample_count = first["count"]
        else:
            sample_name = data.get("sample_name", getattr(self.controller, "sample_name", "Sample 1"))
            sample_volume = data.get("sample_volume", getattr(self.controller, "sample_volume", 0.5))
            sample_count = data.get("sample_count", getattr(self.controller, "sample_count", 1))
            try:
                sample_volume = float(sample_volume)
                if sample_volume <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                sample_volume = getattr(self.controller, "sample_volume", 0.5)
            try:
                sample_count = int(sample_count)
                if sample_count <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                sample_count = getattr(self.controller, "sample_count", 1)
            self.controller.sample_definitions = [{
                "name": str(sample_name).strip() or getattr(self.controller, "sample_name", "Sample 1"),
                "volume": sample_volume,
                "count": sample_count,
            }]
            self.controller.sample_name = self.controller.sample_definitions[0]["name"]
            self.controller.sample_volume = self.controller.sample_definitions[0]["volume"]
            self.controller.sample_count = self.controller.sample_definitions[0]["count"]

        self.controller._refresh_sample_definitions_table()
