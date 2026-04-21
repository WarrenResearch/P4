
import pandas as pd
import time


class SequenceExecutor:
    def __init__(self, controller):
        self.controller = controller

    def wash_step(self, on_complete=None):
        wash_flowrate_total_ml_min = 1.0
        wash_flowrate_ml_min = wash_flowrate_total_ml_min / len(self.controller.pump_widgets) if self.controller.pump_widgets else 0.0
        wash_volume_ml = 1.5 * float(self.controller.reactor_volume_ml)
        wash_duration_s = (wash_volume_ml / wash_flowrate_ml_min) * 60.0
        wash_duration_min = wash_duration_s / 60.0
        wash_duration_ms = int(wash_duration_s * 1000)

        active_pumps = []
        for pump_widget in self.controller.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"):
                continue

            try:
                pump_widget.setFlowrateText.setText(str(wash_flowrate_ml_min))
                pump_widget.setFlowrate()
                pump_widget.start()
                active_pumps.append(pump_widget)
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Wash step skipped for {pump_name}: {error}")

        if not active_pumps:
            print("Wash step aborted: no connected pumps available.")
            return False

        print(
            f"Wash step running at {wash_flowrate_total_ml_min} mL/min for {wash_volume_ml:.2f} mL "
            f"({wash_duration_min:.1f} min)."
        )

        self.controller._schedule_timer(
            wash_duration_ms,
            lambda pumps=active_pumps, callback=on_complete: self._finish_wash_step(pumps, callback),
            track_sequence=True,
        )
        return True

    def _finish_wash_step(self, active_pumps, on_complete=None):
        for pump_widget in active_pumps:
            try:
                pump_widget.setFlowrateText.setText("0.01")
                pump_widget.setFlowrate()
                pump_widget.start()
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Failed to stop {pump_name} after wash step: {error}")

        print("Wash step complete.")
        if callable(on_complete):
            on_complete()

    def _poll_temp_and_handle_row(self):
        current_temp_text = self.controller.thermocontroller.currentTempDisplay.text().strip()
        if not self.controller.temp_reached(current_temp_text):
            self.controller._schedule_timer(2000, self._poll_temp_and_handle_row, track_sequence=True)
            return

        print("Target temperature reached. Starting wash step.")
        self.wash_step(on_complete=self._on_wash_complete_for_row)

    def _on_wash_complete_for_row(self):
        row_data = getattr(self.controller, "_active_sequence_row_data", None)
        if not isinstance(row_data, dict):
            print("No active sequence row found after wash step.")
            return

        total_flow_ml_min = self.controller._apply_row_flowrates(row_data)
        if total_flow_ml_min <= 0:
            print("No valid flowrates in active row; advancing to next row.")
            self._on_row_complete()
            return

        hold_volume_ml = (3.0 * float(self.controller.reactor_volume_ml)) + self.controller.fraction_delay_volume_ml
        hold_duration_s = (hold_volume_ml / total_flow_ml_min) * 60.0
        hold_duration_ms = int(hold_duration_s * 1000)

        print(
            f"Row hold started at total flow {total_flow_ml_min:.3f} mL/min for "
            f"{hold_volume_ml:.2f} mL ({hold_duration_s:.1f} s) (reactor volume x3 + delay volume included)."
        )
        self.controller._schedule_timer(hold_duration_ms, self._on_row_complete, track_sequence=True)

    def _on_row_complete(self):
        current_row = getattr(self.controller, "_sequence_row_index", 0)
        self._sample_current_row(current_row, 1)

    def _sample_current_row(self, current_row, sample_number):
        if not self.controller.update_sample_count():
            self._advance_sequence_after_sample(current_row)
            return

        sample_id = f"row-{current_row + 1}-sample-{sample_number}"
        started = self.controller.fractioncollector_sample(
            sample_id,
            on_complete=lambda row=current_row, sample=sample_number: self.controller._schedule_timer(
                1000,
                lambda r=row, s=sample: self._after_row_sample(r, s),
                track_sequence=True,
            ),
            track_sequence_timer=True,
        )
        if not started:
            self._advance_sequence_after_sample(current_row)

    def _after_row_sample(self, current_row, sample_number):
        if sample_number < self.controller.sample_count:
            self._sample_current_row(current_row, sample_number + 1)
            return

        self._advance_sequence_after_sample(current_row)

    def _handle_sequence_complete(self):
        if not getattr(self.controller, "_sequence_running", False):
            return

        print(f"[{time.strftime('%H:%M:%S')}] Sequence complete.")
        self.stop_sequence()

    def _advance_sequence_after_sample(self, current_row):
        self.controller._sequence_row_index = current_row + 1
        if self.controller._sequence_row_index >= len(self.controller._sequence_df):
            self._handle_sequence_complete()
            return

        self._run_current_row()

    def _run_current_row(self):
        if not getattr(self.controller, "_sequence_running", False):
            return

        if self.controller._sequence_row_index >= len(self.controller._sequence_df):
            self._handle_sequence_complete()
            return

        row_data = self.controller._sequence_df.iloc[self.controller._sequence_row_index].to_dict()
        self.controller._active_sequence_row_data = row_data

        for pump_widget in self.controller.pump_widgets:
            if not hasattr(pump_widget, "pumpObj"):
                continue

            try:
                pump_widget.setFlowrateText.setText("0.01")
                pump_widget.setFlowrate()
                pump_widget.start()
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"{pump_name}: {error}")

        temp_columns = [column for column in self.controller._sequence_df.columns if "Temperature" in column]
        next_temp = row_data.get(temp_columns[0], "") if temp_columns else ""
        if pd.isna(next_temp) or str(next_temp).strip() == "":
            print(f"No temperature value in reactor_sequence row {self.controller._sequence_row_index + 1}.")
            self._on_row_complete()
            return

        self.controller.thermocontroller.targetTempText.setText(str(next_temp).strip())
        self.controller.thermocontroller.setTargetTemperature()
        print(
            f"[{time.strftime('%H:%M:%S')}] Row {self.controller._sequence_row_index + 1}: "
            f"target temperature set to {next_temp} C."
        )

        self._poll_temp_and_handle_row()

    def run_sequence(self):
        self.controller._invalidate_sequence_callbacks()
        self.controller._cancel_sequence_timers()

        self.controller._sequence_df = self.controller.get_sequence_targets_df()
        if self.controller._sequence_df.empty:
            print(f"[{time.strftime('%H:%M:%S')}] reactor_sequence is empty.")
            return False

        temp_columns = [column for column in self.controller._sequence_df.columns if "Temperature" in column]
        if not temp_columns:
            print("No temperature column found in reactor_sequence.")
            return False

        self.controller._sequence_row_index = 0
        self.controller._sequence_running = True
        self._run_current_row()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence started.")
        return True

    def stop_sequence(self):
        self.controller._sequence_running = False
        self.controller._invalidate_sequence_callbacks()
        self.controller._cancel_sequence_timers()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence stopped.")

        try:
            self.controller.thermocontroller.targetTempText.setText("25.0")
            self.controller.thermocontroller.setTargetTemperature()
            print(f"[{time.strftime('%H:%M:%S')}] Temperature set to 25.0 C.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to set temperature: {error}")

        for pump_widget in self.controller.pump_widgets:
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

        try:
            if self.controller._is_fraction_collector_connected():
                self.controller.reset_fraction_collector()
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector reset to HOME.")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector not connected.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to reset fraction collector: {error}")

        print(f"[{time.strftime('%H:%M:%S')}] Sequence stop complete.")
