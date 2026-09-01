import os
import pandas as pd
import time


class SequenceExecutor:
    # This class runs the sequence workflow step-by-step.
    # It keeps sequence orchestration logic out of the main GUI class.
    def __init__(self, controller):
        # Keep a reference to the main platform controller.
        self.controller = controller

    def wash_step(self, on_complete=None):
        # Total wash flow target for all pumps combined.
        wash_flowrate_total_ml_min = 1.0

        # Split total wash flow evenly across available pump widgets.
        wash_flowrate_ml_min = wash_flowrate_total_ml_min / len(self.controller.pump_widgets) if self.controller.pump_widgets else 0.0

        # Wash volume is 1.5 reactor volumes.
        wash_volume_ml = 1.5 * float(self.controller.reactor_volume_ml)

        # Convert volume and flow to duration in seconds.
        wash_duration_s = (wash_volume_ml / wash_flowrate_ml_min) * 60.0
        wash_duration_min = wash_duration_s / 60.0
        wash_duration_ms = int(wash_duration_s * 1000)

        # Track pumps we successfully started, so we can set them back later.
        active_pumps = []
        for pump_widget in self.controller.pump_widgets:
            # Skip widgets that are not connected/configured to real pump objects.
            if not hasattr(pump_widget, "pumpObj"):
                continue

            try:
                # Set each active pump to wash flow and start it.
                pump_widget.setFlowrateText.setText(str(wash_flowrate_ml_min))
                pump_widget.setFlowrate()
                pump_widget.start()
                active_pumps.append(pump_widget)
            except Exception as error:
                # If one pump fails, continue with others and log the issue.
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Wash step skipped for {pump_name}: {error}")

        # If none could run, abort wash step.
        if not active_pumps:
            print("Wash step aborted: no connected pumps available.")
            return False

        print(
            f"[{time.strftime('%H:%M:%S')}] Wash step running at {wash_flowrate_total_ml_min} mL/min for {wash_volume_ml:.2f} mL "
            f"({wash_duration_min:.1f} min)."
        )

        # Schedule wash completion callback after computed duration.
        self.controller._schedule_timer(
            wash_duration_ms,
            lambda pumps=active_pumps, callback=on_complete: self._finish_wash_step(pumps, callback),
            track_sequence=True,
        )
        return True

    def _finish_wash_step(self, active_pumps, on_complete=None):
        # After washing, drop active pumps to low flow (0.01 mL/min).
        for pump_widget in active_pumps:
            try:
                pump_widget.setFlowrateText.setText("0.01")
                pump_widget.setFlowrate()
                pump_widget.start()
            except Exception as error:
                pump_name = pump_widget.nameEdit.text().strip() or "Unnamed pump"
                print(f"Failed to stop {pump_name} after wash step: {error}")

        print(f"[{time.strftime('%H:%M:%S')}] Wash step complete.")

        # Continue sequence chain if caller provided callback.
        if callable(on_complete):
            on_complete()

    def _poll_temp_and_handle_row(self):
        # Read current temperature from thermocontroller display.
        current_temp_text = self.controller.thermocontroller.currentTempDisplay.text().strip()

        # If target temp not reached yet, wait 2 s and check again.
        if not self.controller.temp_reached(current_temp_text):
            self.controller._schedule_timer(2000, self._poll_temp_and_handle_row, track_sequence=True)
            return

        # Once target reached, begin wash step.
        print(f"[{time.strftime('%H:%M:%S')}] Target temperature reached. Starting wash step.")
        self.wash_step(on_complete=self._on_wash_complete_for_row)

    def _on_wash_complete_for_row(self):
        # Read currently active row data prepared by _run_current_row.
        row_data = getattr(self.controller, "_active_sequence_row_data", None)
        if not isinstance(row_data, dict):
            print("No active sequence row found after wash step.")
            return

        # Apply row flowrates to pumps and get total resulting flow.
        total_flow_ml_min = self.controller._apply_row_flowrates(row_data)
        if total_flow_ml_min <= 0:
            print("No valid flowrates in active row; advancing to next row.")
            self._on_row_complete()
            return

        # Hold volume includes 3 reactor volumes plus downstream delay volume.
        hold_volume_ml = (3.0 * float(self.controller.reactor_volume_ml)) + self.controller.fraction_delay_volume_ml
        hold_duration_s = (hold_volume_ml / total_flow_ml_min) * 60.0
        hold_duration_ms = int(hold_duration_s * 1000)

        print(
            f"[{time.strftime('%H:%M:%S')}] Row hold started at total flow {total_flow_ml_min:.3f} mL/min for "
            f"{hold_volume_ml:.2f} mL ({hold_duration_s / 60:.1f} min(s)) (reactor volume x3 + delay volume included)."
        )

        # After hold time, move to row sampling.
        self.controller._schedule_timer(hold_duration_ms, self._on_row_complete, track_sequence=True)

    def _on_row_complete(self):
        # Start sampling sequence for current row.
        current_row = getattr(self.controller, "_sequence_row_index", 0)
        self._sample_current_row(current_row, 1)

    def _sample_current_row(self, current_row, sample_number=1, sample_index=0, sample_plan=None):
        if sample_plan is None:
            sample_plan = self.controller.get_sample_plan()

        if not sample_plan:
            self._advance_sequence_after_sample(current_row)
            return

        if sample_index >= len(sample_plan):
            self._advance_sequence_after_sample(current_row)
            return

        current_sample = sample_plan[sample_index]
        sample_label = str(current_sample.get("name", "Sample")).strip() or "Sample"
        sample_volume = float(current_sample.get("volume", self.controller.sample_volume))
        sample_count = int(current_sample.get("count", self.controller.sample_count))

        self.controller.sample_name = sample_label
        self.controller.sample_volume = sample_volume
        self.controller.sample_count = sample_count

        sample_id = f"{sample_label}-row-{current_row + 1}-sample-{sample_number}"

        started = self.controller.fractioncollector_sample(
            sample_id,
            on_complete=lambda row=current_row, sample=sample_number, index=sample_index, plan=sample_plan: self.controller._schedule_timer(
                1000,
                lambda r=row, s=sample, i=index, p=plan: self._after_row_sample(r, s, i, p),
                track_sequence=True,
            ),
            track_sequence_timer=True,
        )

        if not started:
            self._advance_sequence_after_sample(current_row)

    def _after_row_sample(self, current_row, sample_number, sample_index=0, sample_plan=None):
        if sample_plan is None:
            sample_plan = self.controller.get_sample_plan()
        if not sample_plan:
            self._advance_sequence_after_sample(current_row)
            return

        current_sample = sample_plan[sample_index]
        current_count = int(current_sample.get("count", self.controller.sample_count))

        if sample_number < current_count:
            self._sample_current_row(current_row, sample_number + 1, sample_index, sample_plan)
            return

        if sample_index < len(sample_plan) - 1:
            self._sample_current_row(current_row, 1, sample_index + 1, sample_plan)
            return

        self._advance_sequence_after_sample(current_row)

    def _handle_sequence_complete(self):
        # If sequence already stopped, do nothing.
        if not getattr(self.controller, "_sequence_running", False):
            return

        print(f"[{time.strftime('%H:%M:%S')}] Sequence complete.")
        self.stop_sequence()

    def _advance_sequence_after_sample(self, current_row):
        # Mark the current row complete before moving forward.
        self.controller._apply_sequence_row_style(current_row, "completed")

        # Move row index forward.
        self.controller._sequence_row_index = current_row + 1

        # If no more rows remain, finish sequence.
        if self.controller._sequence_row_index >= len(self.controller._sequence_df):
            self._handle_sequence_complete()
            return

        # Otherwise run next row.
        self._run_current_row()

    def _run_current_row(self):
        # Ignore callbacks if sequence was stopped.
        if not getattr(self.controller, "_sequence_running", False):
            return

        # Safety check: if row index exceeds data length, complete sequence.
        if self.controller._sequence_row_index >= len(self.controller._sequence_df):
            self._handle_sequence_complete()
            return

        # Copy active row data from DataFrame.
        row_data = self.controller._sequence_df.iloc[self.controller._sequence_row_index].to_dict()
        self.controller._active_sequence_row_data = row_data
        self.controller._apply_sequence_row_style(self.controller._sequence_row_index, "active")

        # While waiting for target temperature, run connected pumps at low flow.
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

        # Find temperature column and read target value for this row.
        temp_columns = [column for column in self.controller._sequence_df.columns if "Temperature" in column]
        next_temp = row_data.get(temp_columns[0], "") if temp_columns else ""

        # If row has no target temperature, skip to sampling path.
        if pd.isna(next_temp) or str(next_temp).strip() == "":
            print(f"No temperature value in reactor_sequence row {self.controller._sequence_row_index + 1}.")
            self._on_row_complete()
            return

        # Push target temperature to thermocontroller.
        self.controller.thermocontroller.targetTempText.setText(str(next_temp).strip())
        self.controller.thermocontroller.setTargetTemperature()
        print(
            f"[{time.strftime('%H:%M:%S')}] Row {self.controller._sequence_row_index + 1}: "
            f"target temperature set to {next_temp} C."
        )

        # Start polling until target temperature is reached.
        self._poll_temp_and_handle_row()

    def run_sequence(self):
        # Invalidate any old callbacks and clear old timers.
        self.controller._invalidate_sequence_callbacks()
        self.controller._cancel_sequence_timers()

        # Read latest sequence table into DataFrame snapshot.
        self.controller._sequence_df = self.controller.get_sequence_targets_df()
        if self.controller._sequence_df.empty:
            print(f"[{time.strftime('%H:%M:%S')}] reactor_sequence is empty.")
            return False

        # Require at least one temperature column.
        temp_columns = [column for column in self.controller._sequence_df.columns if "Temperature" in column]
        if not temp_columns:
            print("No temperature column found in reactor_sequence.")
            return False

        # Initialize sequence state and launch first row.
        self.controller._sequence_row_index = 0
        self.controller._sequence_running = True
        self.controller._reset_sequence_row_styles()
        self._run_current_row()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence started.")
        return True

    def stop_sequence(self):
        # Stop flag prevents further scheduled callbacks from executing sequence logic.
        current_row = getattr(self.controller, "_sequence_row_index", None)
        if (
            isinstance(current_row, int)
            and self.controller._sequence_row_states.get(current_row) == "active"
        ):
            self.controller._apply_sequence_row_style(current_row, "idle")

        self.controller._sequence_running = False
        self.controller._invalidate_sequence_callbacks()
        self.controller._cancel_sequence_timers()
        print(f"[{time.strftime('%H:%M:%S')}] Sequence stopped.")

        # Save the active sequence dataframe before shutting hardware down.
        try:
            log_dir = "Sequence_logs"
            os.makedirs(log_dir, exist_ok=True)

            start_time_for_log = self.controller._get_monitor_start_time_str()
            log_path = os.path.join(log_dir, f"Sequence_log_{start_time_for_log}.csv")

            sequence_df = getattr(self.controller, "_sequence_df", None)
            if sequence_df is None:
                sequence_df = self.controller.get_sequence_targets_df()

            sequence_df.to_csv(log_path, index=False)
            print(f"[{time.strftime('%H:%M:%S')}] Sequence log saved to {log_path}")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to save sequence log: {error}")


        # Reset thermocontroller to 25 C.
        try:
            self.controller.thermocontroller.targetTempText.setText("25.0")
            self.controller.thermocontroller.setTargetTemperature()
            print(f"[{time.strftime('%H:%M:%S')}] Temperature set to 25.0 C.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to set temperature: {error}")

        # Set each connected pump to 0.1 mL/min and issue stop.
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

        # Reset fraction collector to HOME if connected.
        try:
            if self.controller._is_fraction_collector_connected():
                self.controller.reset_fraction_collector()
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector reset to HOME.")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector not connected.")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to reset fraction collector: {error}")

        print(f"[{time.strftime('%H:%M:%S')}] Sequence stop complete.")
