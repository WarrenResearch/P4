import time
from PyQt5 import QtWidgets


class FractionCollectorHandler:
    # This class groups all fraction collector actions in one place.
    # It uses the main controller to access UI widgets and shared methods.
    def __init__(self, controller):
        # Keep a reference to the main platform controller.
        self.controller = controller

    def _is_fraction_collector_connected(self):
        # Treat an existing socket as "connected".
        return getattr(self.controller.fractioncollector, "sock", None) is not None

    def connect_fraction_collector(self):
        # Try to ensure we have an active connection and remote mode enabled.
        try:
            # If already connected, do nothing and report success.
            if self._is_fraction_collector_connected():
                print("Fraction collector already connected.")
                return True

            # Open connection to the hardware.
            self.controller.fractioncollector.connect()

            # Update button label so user sees connected status.
            self.controller.fractionConnectButton.setText("Fraction Collector Connected")

            # Keep device in remote mode indefinitely.
            self.controller.fractioncollector.set_remote(timeout_ms=0)
            return True
        except Exception as error:
            # If connection fails, print reason and report failure.
            print(f"[{time.strftime('%H:%M:%S')}] Failed to connect fraction collector: {error}")
            return False

    def _retry_fraction_collector_command(self, command_name, command_callback):
        # Run command once; on connection drop, reconnect and retry once.
        try:
            return command_callback()
        except ConnectionError as error:
            print(f"[{time.strftime('%H:%M:%S')}] Fraction collector connection lost during {command_name}: {error}")

            # Reconnect before retrying.
            if not self.connect_fraction_collector():
                return False

            try:
                return command_callback()
            except Exception as retry_error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to {command_name} after reconnect: {retry_error}")
                return False

    def disconnect_fraction_collector(self):
        # Disconnect the hardware and update button text.
        try:
            # If already disconnected, just inform user.
            if not self._is_fraction_collector_connected():
                print(f"[{time.strftime('%H:%M:%S')}] Fraction collector is not connected.")
                return

            self.controller.fractioncollector.disconnect()
            self.controller.fractionConnectButton.setText("Connect Fraction Collector")
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to disconnect fraction collector: {error}")

    def move_to_next_position(self):
        # Move to next vial position.
        if not self._is_fraction_collector_connected():
            print(f"[{time.strftime('%H:%M:%S')}] Connect the fraction collector first.")
            return

        try:
            self.controller.fractioncollector.move_next()
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to next position: {error}")

    def move_fraction_collector(self):
        # Read target position from UI and normalize text.
        position = self.controller.fractionMovePositionText.text().strip().upper()
        if not position:
            print(f"[{time.strftime('%H:%M:%S')}] Please enter a move position (e.g. A1).")
            return

        try:
            # Ensure remote mode, then move.
            self.controller.fractioncollector.set_remote(timeout_ms=0)
            self.controller.fractioncollector.move_to_vial(position)
            print(f"[{time.strftime('%H:%M:%S')}] Moved to {position}")

        except ConnectionError:
            # Connection dropped while moving.
            print(f"[{time.strftime('%H:%M:%S')}] Connection lost. Please click Connect again.")
            self.controller.fractionConnectButton.setText("Connect Fraction Collector")

        except Exception as error:
            # Other move failure: log and try one additional move attempt.
            print(f"[{time.strftime('%H:%M:%S')}] Failed to move: {error}")

            try:
                self.controller.fractioncollector.move_to_vial(position)
            except Exception as move_error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to {position}: {move_error}")

    def reset_fraction_collector(self):
        # Reset means move to HOME.
        self.controller.fractionMovePositionText.setText("HOME")
        self.move_fraction_collector()

    def fractioncollector_sample(self, sample_id, on_complete=None, track_sequence_timer=False):
        # Validate sample volume from UI.
        if not self.controller.update_sample_volume():
            return False

        # Sum all pump flowrates.
        total_flow_ml_min = self.controller._get_total_current_flowrate_ml_min()

        # Cannot compute sampling duration with zero/negative flow.
        if total_flow_ml_min <= 0:
            QtWidgets.QMessageBox.warning(
                self.controller,
                "Sample duration",
                "Cannot calculate sample duration: total flowrate must be greater than 0 mL/min.",
            )
            return False

        # Convert requested sample volume to required sample time in seconds.
        self.controller.sample_duration = (self.controller.sample_volume / total_flow_ml_min) * 60.0
        print(
            f"Sample duration calculated from volume/flowrate: "
            f"{self.controller.sample_volume:.3f} mL / {total_flow_ml_min:.3f} mL/min = {self.controller.sample_duration:.1f} s"
        )

        # Guard clause: if connection cannot be established, abort sampling.
        if not self.connect_fraction_collector():
            return False

        # Move to the next vial with reconnect+retry support.
        if not self._retry_fraction_collector_command(
            "move fraction collector to next vial",
            lambda: self.controller.fractioncollector.move_next(collect_mode=0),
        ):
            return False

        # Delay one second, then start collection.
        self.controller._schedule_timer(
            1000,
            lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete, track=track_sequence_timer: self._start_fractioncollector_collection(sid, flow, callback, track),
            track_sequence=track_sequence_timer,
        )
        return True

    def _start_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None, track_sequence_timer=False):
        # Re-check connection before issuing start command.
        if not self.connect_fraction_collector():
            if callable(on_complete):
                on_complete()
            return

        # Start collecting sample, with reconnect+retry behavior.
        if not self._retry_fraction_collector_command(
            "start sample collection",
            lambda: self.controller.fractioncollector.set_collect(1),
        ):
            if callable(on_complete):
                on_complete()
            return

        print(f"Starting sample collection for {self.controller.sample_duration:.1f} s.")

        # Schedule stop after computed duration.
        duration_ms = max(0, int(self.controller.sample_duration * 1000))
        self.controller._schedule_timer(
            duration_ms,
            lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete: self._finish_fractioncollector_collection(sid, flow, callback),
            track_sequence=track_sequence_timer,
        )

    def _finish_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None):
        # Parameter kept for signature compatibility.
        _ = total_flow_ml_min

        # Re-check connection before issuing stop command.
        if not self.connect_fraction_collector():
            if callable(on_complete):
                on_complete()
            return

        # Stop collecting sample, with reconnect+retry behavior.
        if not self._retry_fraction_collector_command(
            "stop sample collection",
            lambda: self.controller.fractioncollector.set_collect(0),
        ):
            print("Failed to stop sample collection.")
        else:
            print(f"Sample taken: {sample_id}")

        # Read current collector position.
        current_position = self.controller.fractioncollector.position()

        # If monitor exists, write sample event to log.
        if self.controller.main is not None and hasattr(self.controller.main, "platform_monitor"):
            event_text = (
                f"SAMPLE_TAKEN;id={sample_id};"
                f"volume_ml={self.controller.sample_volume:.3f};"
                f"fraction_collector_position={current_position}"
            )
            try:
                self.controller.main.platform_monitor.continuous_log_function(event=event_text)
            except Exception as error:
                print(f"Failed to log sample event in platform monitor: {error}")

        # Try to write position into reactor sequence table.
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Fraction collector position at sample: {current_position}")
            current_row = getattr(self.controller, "_sequence_row_index", 0)
            col_index = None

            # Find the "Fraction Collector Position" column.
            for col in range(self.controller.targetsTable.columnCount()):
                header_item = self.controller.targetsTable.horizontalHeaderItem(col)
                if header_item and header_item.text() == "Fraction Collector Position":
                    col_index = col
                    break

            # If column exists, write current position into current row.
            if col_index is not None:
                self.controller.targetsTable.setItem(current_row, col_index, QtWidgets.QTableWidgetItem(str(current_position)))
        except Exception as error:
            print(f"Failed to capture fraction collector position: {error}")

        # Notify caller that sample cycle is complete.
        if callable(on_complete):
            on_complete()
