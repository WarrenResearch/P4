import time
from PyQt5 import QtWidgets


class FractionCollectorHandler:
	def __init__(self, controller):
		self.controller = controller

	def _is_fraction_collector_connected(self):
		return getattr(self.controller.fractioncollector, "sock", None) is not None

	def connect_fraction_collector(self):
		try:
			if self._is_fraction_collector_connected():
				print("Fraction collector already connected.")
				return True
			self.controller.fractioncollector.connect()
			self.controller.fractionConnectButton.setText("Fraction Collector Connected")
			self.controller.fractioncollector.set_remote(timeout_ms=0)
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
			self.controller.fractioncollector.disconnect()
			self.controller.fractionConnectButton.setText("Connect Fraction Collector")
		except Exception as error:
			print(f"[{time.strftime('%H:%M:%S')}] Failed to disconnect fraction collector: {error}")

	def move_to_next_position(self):
		if not self._is_fraction_collector_connected():
			print(f"[{time.strftime('%H:%M:%S')}] Connect the fraction collector first.")
			return

		try:
			self.controller.fractioncollector.move_next()
		except Exception as error:
			print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to next position: {error}")

	def move_fraction_collector(self):
		position = self.controller.fractionMovePositionText.text().strip().upper()
		if not position:
			print(f"[{time.strftime('%H:%M:%S')}] Please enter a move position (e.g. A1).")
			return

		try:
			self.controller.fractioncollector.set_remote(timeout_ms=0)
			self.controller.fractioncollector.move_to_vial(position)
			print(f"[{time.strftime('%H:%M:%S')}] Moved to {position}")

		except ConnectionError:
			print(f"[{time.strftime('%H:%M:%S')}] Connection lost. Please click Connect again.")
			self.controller.fractionConnectButton.setText("Connect Fraction Collector")

		except Exception as error:
			print(f"[{time.strftime('%H:%M:%S')}] Failed to move: {error}")

			try:
				self.controller.fractioncollector.move_to_vial(position)
			except Exception as move_error:
				print(f"[{time.strftime('%H:%M:%S')}] Failed to move fraction collector to {position}: {move_error}")

	def reset_fraction_collector(self):
		self.controller.fractionMovePositionText.setText("HOME")
		self.move_fraction_collector()

	def fractioncollector_sample(self, sample_id, on_complete=None, track_sequence_timer=False):
		if not self.controller.update_sample_volume():
			return False

		total_flow_ml_min = self.controller._get_total_current_flowrate_ml_min()
		if total_flow_ml_min <= 0:
			QtWidgets.QMessageBox.warning(
				self.controller,
				"Sample duration",
				"Cannot calculate sample duration: total flowrate must be greater than 0 mL/min.",
			)
			return False

		self.controller.sample_duration = (self.controller.sample_volume / total_flow_ml_min) * 60.0
		print(
			f"Sample duration calculated from volume/flowrate: "
			f"{self.controller.sample_volume:.3f} mL / {total_flow_ml_min:.3f} mL/min = {self.controller.sample_duration:.1f} s"
		)

		if not self.connect_fraction_collector():
			return False

		if not self._retry_fraction_collector_command(
			"move fraction collector to next vial",
			lambda: self.controller.fractioncollector.move_next(collect_mode=0),
		):
			return False

		self.controller._schedule_timer(
			1000,
			lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete, track=track_sequence_timer: self._start_fractioncollector_collection(sid, flow, callback, track),
			track_sequence=track_sequence_timer,
		)
		return True

	def _start_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None, track_sequence_timer=False):
		if not self.connect_fraction_collector():
			if callable(on_complete):
				on_complete()
			return

		if not self._retry_fraction_collector_command(
			"start sample collection",
			lambda: self.controller.fractioncollector.set_collect(1),
		):
			if callable(on_complete):
				on_complete()
			return

		print(f"Starting sample collection for {self.controller.sample_duration:.1f} s.")

		duration_ms = max(0, int(self.controller.sample_duration * 1000))
		self.controller._schedule_timer(
			duration_ms,
			lambda sid=sample_id, flow=total_flow_ml_min, callback=on_complete: self._finish_fractioncollector_collection(sid, flow, callback),
			track_sequence=track_sequence_timer,
		)

	def _finish_fractioncollector_collection(self, sample_id, total_flow_ml_min, on_complete=None):
		_ = total_flow_ml_min
		if not self.connect_fraction_collector():
			if callable(on_complete):
				on_complete()
			return

		if not self._retry_fraction_collector_command(
			"stop sample collection",
			lambda: self.controller.fractioncollector.set_collect(0),
		):
			print("Failed to stop sample collection.")
		else:
			print(f"Sample taken: {sample_id}")

		current_position = self.controller.fractioncollector.position()

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

		try:
			print(f"[{time.strftime('%H:%M:%S')}] Fraction collector position at sample: {current_position}")
			current_row = getattr(self.controller, "_sequence_row_index", 0)
			col_index = None
			for col in range(self.controller.targetsTable.columnCount()):
				header_item = self.controller.targetsTable.horizontalHeaderItem(col)
				if header_item and header_item.text() == "Fraction Collector Position":
					col_index = col
					break
			if col_index is not None:
				self.controller.targetsTable.setItem(current_row, col_index, QtWidgets.QTableWidgetItem(str(current_position)))
		except Exception as error:
			print(f"Failed to capture fraction collector position: {error}")

		if callable(on_complete):
			on_complete()
