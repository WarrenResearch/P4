import os
import re
import pandas as pd

# Fixed (non-pump) sequence columns.
RESIDENCE_COL = "Residence time [min]"
TEMP_COL = "Temperature [°C]"
FC_COL = "Fraction Collector Position"


# Sequence modes. The first is the core behaviour; the others add optional columns.
MODE_FLOWRATE = "Flowrates [mL/min]"
MODE_RESIDENCE = "Residence time + ratio"
MODE_MONOMER = "Residence time + ratio + monomer %"
SEQUENCE_MODES = [MODE_FLOWRATE, MODE_RESIDENCE, MODE_MONOMER]


def flow_col(pump_name):
    return f"{pump_name} [mL/min]"


def ratio_col(pump_name):
    return f"{pump_name} ratio"


def monomer_col(pump_name):
    return f"{pump_name} monomer [%]"


def build_headers(pump_names, mode=MODE_FLOWRATE):
    headers = []
    for name in pump_names:
        if mode == MODE_FLOWRATE:
            headers.append(flow_col(name))
        else:
            headers.append(ratio_col(name))
            if mode == MODE_MONOMER:
                # Optional per-pump feed concentration (% monomer); recorded, not yet used for flow.
                headers.append(monomer_col(name))
    if mode != MODE_FLOWRATE:
        headers.append(RESIDENCE_COL)
    headers.extend([TEMP_COL, FC_COL])
    return headers


def template_df(pump_names, mode=MODE_FLOWRATE, example_rows=1):
    # Empty design sheet with the current platform headers.
    headers = build_headers(pump_names, mode)
    return pd.DataFrame([[""] * len(headers)] * example_rows, columns=headers)


def _normalise(header):
    # Case/space/unit-insensitive key, e.g. "Pump 1 Monomer [%]" -> "pump1monomer".
    text = re.sub(r"\[.*?\]|\(.*?\)", "", str(header)).lower()
    return re.sub(r"[^a-z0-9]", "", text)


def read_design_file(path):
    # Read a design as strings so blanks and formats are preserved exactly.
    extension = os.path.splitext(path)[1].lower()
    if extension in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, dtype=str).fillna("")
    if extension in (".csv", ".txt"):
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    raise ValueError(f"Unsupported file type '{extension}'. Use .csv or .xlsx.")


def _to_float(value):
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def match_design(file_df, table_headers):
    """Map a design DataFrame onto the table headers.

    Returns (table_df, warnings). table_df has exactly table_headers as columns,
    all values strings; unmatched table columns are blank, invalid cells are
    blanked and reported by row number.
    """
    warnings = []
    table_keys = {_normalise(header): header for header in table_headers}

    mapping = {}
    ignored = []
    for file_col in file_df.columns:
        header = table_keys.get(_normalise(file_col))
        if header is not None and header not in mapping.values():
            mapping[file_col] = header
        else:
            ignored.append(str(file_col))

    if ignored:
        warnings.append("Ignored file columns (no matching platform column): " + ", ".join(ignored))
    if RESIDENCE_COL in table_headers and RESIDENCE_COL not in mapping.values():
        warnings.append(f"No '{RESIDENCE_COL}' column found; rows cannot be run until it is filled in.")

    table_df = pd.DataFrame("", index=range(len(file_df)), columns=table_headers)
    for file_col, header in mapping.items():
        table_df[header] = file_df[file_col].astype(str).str.strip().values

    # Validate numeric ranges; blank bad cells so they cannot reach the pumps.
    for header in table_headers:
        if header == FC_COL:
            continue
        for row, value in table_df[header].items():
            if value == "":
                continue
            try:
                number = _to_float(value)
            except ValueError:
                problem = "is not a number"
            else:
                problem = None
                if header == RESIDENCE_COL and number <= 0:
                    problem = "must be > 0"
                elif (header.endswith(" ratio") or header.endswith("[mL/min]")) and number < 0:
                    problem = "must be >= 0"
                elif header.endswith("monomer [%]") and not 0 <= number <= 100:
                    problem = "must be between 0 and 100"
            if problem:
                warnings.append(f"Row {row + 1}, '{header}': '{value}' {problem}; cell cleared.")
                table_df.at[row, header] = ""

    ratio_headers = [header for header in table_headers if header.endswith(" ratio")]
    for row in range(len(table_df)):
        message = ratio_sum_warning(table_df.iloc[row].to_dict(), [h[: -len(" ratio")] for h in ratio_headers])
        if message:
            warnings.append(f"Row {row + 1}: {message}")

    return table_df, warnings


def ratio_sum_warning(row_data, pump_names):
    # Ratios are normalised, so a typo (0.25 + 0.85) would silently run as 23/77. Flag sums other than 1 or 100.
    values = []
    for name in pump_names:
        try:
            value = _to_float(row_data.get(ratio_col(name), ""))
        except ValueError:
            continue
        if value is not None:
            values.append(value)
    if not values:
        return None

    ratio_sum = sum(values)
    if abs(ratio_sum - 1) <= 1e-3 or abs(ratio_sum - 100) <= 0.1:
        return None
    return f"pump ratios sum to {ratio_sum:g} (expected 1 or 100); flows will be scaled to the ratios as entered."


def total_flowrate_ml_min(reactor_volume_ml, residence_time_min):
    # Total flow that gives the requested residence time in the reactor.
    return float(reactor_volume_ml) / float(residence_time_min)


def pump_flowrates(row_data, pump_names, reactor_volume_ml, mode=MODE_FLOWRATE):
    """Return {pump_name: mL/min} for one sequence row.

    MODE_FLOWRATE: flows are read straight from the '<pump> [mL/min]' cells
    (blank/invalid cells are skipped). Otherwise:

    Total flow = reactor volume / residence time, split by the pumps' ratio
    cells. If every ratio is blank the split is equal; otherwise a blank ratio
    counts as 0. Returns {} if the row has no valid residence time.
    """
    if mode == MODE_FLOWRATE:
        flows = {}
        for name in pump_names:
            try:
                value = _to_float(row_data.get(flow_col(name), ""))
            except ValueError:
                continue
            if value is not None and value >= 0:
                flows[name] = value
        return flows

    try:
        residence = _to_float(row_data.get(RESIDENCE_COL, ""))
    except ValueError:
        return {}
    if residence is None or residence <= 0 or not pump_names:
        return {}

    total = total_flowrate_ml_min(reactor_volume_ml, residence)

    ratios = {}
    for name in pump_names:
        try:
            ratios[name] = _to_float(row_data.get(ratio_col(name), ""))
        except ValueError:
            ratios[name] = None

    if all(value is None for value in ratios.values()):
        ratios = {name: 1.0 for name in pump_names}
    ratios = {name: (value or 0.0) for name, value in ratios.items()}

    ratio_sum = sum(ratios.values())
    if ratio_sum <= 0:
        return {}
    return {name: total * value / ratio_sum for name, value in ratios.items()}
