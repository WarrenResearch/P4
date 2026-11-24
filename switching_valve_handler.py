import time
from PyQt5 import QtWidgets


class SwitchingValveHandler:
    # Groups the switching-valve sampling action, mirroring FractionCollectorHandler.
    # It uses the main controller to access UI widgets and shared methods.
    def __init__(self, controller):
        self.controller = controller

    def _get_sample_valve(self):
        # Same lookup as GPC_handler: valve5 (legacy layout), then a valve named
        # outlet/sample/gpc, then the only valve if there is just one.
        valve = getattr(self.controller, "valve5", None)
        if valve is not None:
            return valve

        valves = getattr(self.controller, "valve_widgets", [])
        for candidate in valves:
            if candidate.nameEdit.text().strip().lower() in {"outlet", "sample", "gpc"}:
                return candidate
        if len(valves) == 1:
            return valves[0]
        return None

    def _build_conditions(self, reactor_volumes):
        # Conditions recorded with the GPC result: row, reactor volumes, target temperature,
        # total flow and residence time (reactor volume / total flow).
        controller = self.controller
        conditions = {"reactor_volumes": reactor_volumes}
        try:
            conditions["row"] = int(getattr(controller, "_sequence_row_index", 0)) + 1
        except (TypeError, ValueError):
            pass
        try:
            conditions["target_temp_C"] = float(controller.thermocontroller.targetTempText.text())
        except Exception:
            pass
        try:
            flow = float(controller._get_total_current_flowrate_ml_min())
            conditions["total_flow_ml_min"] = round(flow, 4)
            if flow > 0:
                conditions["residence_time_min"] = round(float(controller.reactor_volume_ml) / flow, 3)
        except Exception:
            pass
        return conditions

    def switching_valve_sample(self, sample_id, on_complete=None, track_sequence_timer=False, reactor_volumes=None):
        # Single injection: fire the valve once.
        # Triple injection: fire the valve 3 times, injection_wait_s apart, so GPC
        # injections do not overlap (same strategy as the GPC runner).
        # on_complete is called once the last injection has been fired.
        controller = self.controller
        valve = self._get_sample_valve()
        if valve is None:
            QtWidgets.QMessageBox.warning(
                controller,
                "Switching valve",
                "No sample valve found. Add a valve named Outlet/Sample/GPC (or configure five valves).",
            )
            return False

        injnum = 3 if controller.valve_injection == "Triple" else 1
        wait_s = float(controller.injection_wait_s)

        # Put the conditions in the sample ID so the saved GPC data is self-describing.
        conditions = self._build_conditions(reactor_volumes)
        if "target_temp_C" in conditions:
            sample_id = f"{sample_id}_T{conditions['target_temp_C']:g}C"
        if "residence_time_min" in conditions:
            sample_id = f"{sample_id}_tau{conditions['residence_time_min']:.1f}min"

        print(
            f"[{time.strftime('%H:%M:%S')}] Switching valve sample {sample_id}: "
            f"{injnum} injection(s), {wait_s:g} s apart."
        )

        # If the GPC is connected, let it run the injections and the measurement so they stay in sync.
        gpc_runner = getattr(controller.main, "GPC_runner", None) if controller.main is not None else None
        if gpc_runner is not None and getattr(gpc_runner, "TC08connected", False):
            if not gpc_runner.start_injection(injnum, sample_id, wait_s, conditions):
                return False
        else:
            print(f"[{time.strftime('%H:%M:%S')}] GPC not connected: actuating the valve only.")
            self._fire_valve(valve, 1, injnum, wait_s, track_sequence_timer)

        self._log_event(sample_id, injnum)

        # Sequence carries on once the last injection has been fired.
        controller._schedule_timer(
            ((injnum - 1) * wait_s + 1.0) * 1000,
            lambda: on_complete() if callable(on_complete) else None,
            track_sequence=track_sequence_timer,
        )
        return True

    def _fire_valve(self, valve, number, injnum, wait_s, track_sequence_timer):
        # Fire injection `number`, then schedule the next one after wait_s.
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Valve injection {number} of {injnum}.")
            valve.valveSample()
        except Exception as error:
            print(f"[{time.strftime('%H:%M:%S')}] Valve injection {number} failed: {error}")
        if number < injnum:
            self.controller._schedule_timer(
                wait_s * 1000,
                lambda: self._fire_valve(valve, number + 1, injnum, wait_s, track_sequence_timer),
                track_sequence=track_sequence_timer,
            )

    def _log_event(self, sample_id, injnum):
        main = self.controller.main
        if main is not None and hasattr(main, "platform_monitor"):
            try:
                main.platform_monitor.continuous_log_function(
                    event=f"SAMPLE_TAKEN;id={sample_id};method=switching_valve;injections={injnum}"
                )
            except Exception as error:
                print(f"Failed to log valve sample event in platform monitor: {error}")
