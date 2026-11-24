import os
import pickle
import re
import datetime

import numpy as np
import pandas as pd

# Sits beside Experimental_logs / Sequence_logs (relative to where the app is launched).
RESULTS_ROOT = "GPC_results"

SUMMARY_COLUMNS = [
    "sample_id", "injection_start", "injections", "row", "reactor_volumes",
    "target_temp_C", "residence_time_min", "total_flow_ml_min",
    "Mn", "Mw", "PD", "MP", "trace_file",
]

_session_folder = None


def _safe(name):
    # Make a sample ID safe to use as a file name.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_") or "sample"


def get_run_folder(run_tag=None):
    # One folder per run: GPC_results/<run start time>. run_tag matches the
    # Experimental_log / Sequence_log start time when available.
    global _session_folder
    if run_tag:
        folder = os.path.join(RESULTS_ROOT, _safe(run_tag))
    else:
        # No run tag (e.g. manual injections): reuse one timestamped folder for the session.
        if _session_folder is None:
            _session_folder = os.path.join(RESULTS_ROOT, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        folder = _session_folder
    os.makedirs(folder, exist_ok=True)
    return folder


def save_result(results, run_tag=None):
    """Save one finished GPC result and append it to the run's summary CSV.

    Writes (all in GPC_results/<run>/):
      <sample_id>_<time>.csv  full trace: Time, RI_raw (ch1), RI_corrected (baseline subtracted), UV (ch2)
      <sample_id>_<time>.pkl  full result dict (loadable with "Load GPC data")
      GPC_summary.csv         one row per sample with its conditions
    Mn/Mw/PD/MP are blank until a calibration curve exists.
    Returns the trace file path.
    """
    folder = get_run_folder(run_tag)
    conditions = results.get("conditions") or {}
    sample_id = results.get("sampleID") or "sample"
    start = results["StartTime"][0]
    stamp = start.strftime("%Y%m%d-%H%M%S")
    base = f"{_safe(sample_id)}_{stamp}"

    # One CSV per sample (a triple injection stays in one file, as the baseline is fitted
    # through the whole trace): Time (s since measurement start), RI_raw (ch1),
    # RI_corrected (baseline subtracted), UV (ch2).
    trace = results["rawchrom"].copy()
    if "RI_corrected" in results:
        trace.insert(trace.columns.get_loc("RI") + 1 if "RI" in trace.columns else len(trace.columns),
                     "RI_corrected", results["RI_corrected"])
    if "RI" in trace.columns:
        trace = trace.rename(columns={"RI": "RI_raw"})
    trace_path = os.path.join(folder, base + ".csv")
    trace.to_csv(trace_path, index=False)

    with open(os.path.join(folder, base + ".pkl"), "wb") as handle:
        pickle.dump([results], handle)

    averages = results.get("Averages")
    def _avg(col):
        try:
            value = float(averages[col].values[0])
            return "" if np.isnan(value) else value
        except Exception:
            return ""

    row = {
        "sample_id": sample_id,
        "injection_start": "; ".join(results.get("injection_times") or [start.strftime("%Y-%m-%d %H:%M:%S")]),
        "injections": results.get("injnum", ""),
        "row": conditions.get("row", ""),
        "reactor_volumes": conditions.get("reactor_volumes", ""),
        "target_temp_C": conditions.get("target_temp_C", ""),
        "residence_time_min": conditions.get("residence_time_min", ""),
        "total_flow_ml_min": conditions.get("total_flow_ml_min", ""),
        "Mn": _avg("Mn"), "Mw": _avg("Mw"), "PD": _avg("PD"), "MP": _avg("MP"),
        "trace_file": os.path.basename(trace_path),
    }
    summary_path = os.path.join(folder, "GPC_summary.csv")
    pd.DataFrame([row], columns=SUMMARY_COLUMNS).to_csv(
        summary_path, mode="a", index=False, header=not os.path.isfile(summary_path)
    )
    print(f"GPC result saved to {trace_path}")
    return trace_path
