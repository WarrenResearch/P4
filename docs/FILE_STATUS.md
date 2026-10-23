# File status

A map of every file in the repository root and its subfolders: what it does, whether the running application uses it, and what is known (and not known) about it.

## How this was produced, and how far to trust it

Everything below was checked directly against the code in this repository (imports, class/function names, docstrings, `diff` between near-duplicate files, `git` history). Nothing was run: the application was **not** launched and no hardware was connected, so statements about runtime behaviour are limited to what the code says.

Where the code does not answer a question, the table says **Unknown** rather than guessing. Several of those questions have since been answered by the maintainer; those answers are marked **(maintainer)** below and listed under [Maintainer answers](#maintainer-answers). Anything still unanswered is under [Still open](#still-open).

### Status labels

| Label | Meaning (how it was determined) |
|---|---|
| **Active** | Reachable from `_Main_GUI.py` through `import` statements (directly, indirectly, or via an import inside a function). See the import chain below. |
| **Active (legacy API)** | Reachable from `_Main_GUI.py`, but contains code that refers to names that the current `PlatformControl` does not define. **(maintainer)** This is the legacy Method builder: it is not currently used and is expected to be rebuilt. See [Method builder tab](#method-builder-tab-legacy-to-be-rebuilt). |
| **Legacy (maintainer)** | The maintainer has confirmed the file is an old version or no longer relevant. |
| **Standalone** | Has its own entry point (`if __name__ == "__main__"`) and is not imported by the main application. |
| **Unreferenced** | No other `.py` file in the repo imports it. This alone does not prove it is unused. **(maintainer)** For `picoThermocouples.py`, `PicoGPC_old.py`, `OLDoptimiser.py`, `latinHypercubeSampling.py` and `calculateHypervolume.py`, nothing outside this repo uses them either. |
| **Duplicate / variant** | A near-copy of another file; the difference is stated. |
| **Data / artefact** | Not source code. |

"Safe to delete" is deliberately not a column. That judgement depends on how the files are used outside this repo, which the code cannot tell us.

## Entry point and import chain

Run the application with `_Main_GUI.py` (it is the only file that builds the main window; see `README.md`). It creates five tabs, each constructed as `Tab(self, main=self)`:

| Tab title | Class | File |
|---|---|---|
| Method builder | `ExperimentMethod` | `experimentMethod.py` |
| Platform control | `PlatformControl` | `platformControl.py` |
| GPC calibration | `GPC_calibration` | `GPC_calibration.py` |
| GPC analysis runner | `GPC_runner` | `GPC_runner.py` |
| Platform Monitor | `PlatformMonitor` | `platform_monitor.py` |

Everything marked **Active** below is reached from one of these five files.

---

## Core application

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `_Main_GUI.py` | Main window; creates the five tabs; on close, stops the Pico GPC measurement and the GPC scheduler. | Active | Only file with a GUI entry point. Header credits Peter Pittaway, University of Leeds, 2023. |
| `platformControl.py` | "Platform control" tab: holds the list of pump and valve widgets, thermocontroller, sequence table, sample definitions, reactor and fraction-delay volumes. Delegates to three helper objects (below). | Active | Creates `SequenceExecutor`, `FractionCollectorHandler` and `PlatformConfigHandler` (lines 225–227). Many of its fraction-collector methods are one-line wrappers that call `self.fraction_handler`. Also builds an `AzuraFC61` in its constructor and hard-codes `fraction_delay_volume_ml = 0.556`. |
| `sequence_manager.py` | `SequenceExecutor`: steps through the rows of the sequence table (set temperature, wait, wash step, apply flow rates, sample). | Active | Flowchart: `mermaid_graphs/sequence_manager.mmd`. |
| `fraction_collector_handler.py` | `FractionCollectorHandler`: connect/disconnect, move, sample, clean-dead-volume and run-sample-plan logic for the fraction collector. | Active | Called from `platformControl.py`. |
| `platform_config.py` | `PlatformConfigHandler`: saves and loads the platform layout to `platform_layout.json` (next to the source file). | Active | `_platform_file_path()` returns `<this file's folder>/platform_layout.json`. |
| `platform_layout.json` | The saved platform layout (pumps, valves, thermocontroller, reactor volume, fraction delay volume, sample definitions). | Data / artefact | The committed copy has empty `pumps` and `valves` lists. Written by `platform_config.py`. |
| `platform_monitor.py` | "Platform Monitor" tab: live plots of temperature and pump flow/pressure, and CSV logging. | Active | Writes one `Experimental_log_<timestamp>.csv` per run into `Experimental_logs/` (relative to the working directory). Imports `jasco2080` and `pumpWidget`. |

## Device widgets and drivers

Each widget file is a Qt panel used inside the Platform control tab; the driver files talk to the hardware.

### Pumps

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `pumpWidget.py` | `PumpControl` widget. Pump model dropdown: Teledyne, MilliGAT LF, MilliGAT HF, Chemyx Nexus 4000, Chemyx Fusion 6000X, Chemyx Fusion 4000X, Jasco PU2080. Holds per-pump flow-rate calibration factor and history (`calibration_history.json`). Offers droplet-counter and mass-balance calibration. | Active | Imports the five pump drivers at the top; imports `droplet_calibration` and `mass_calibration` only when a calibration is started (inside a function). **Naming inconsistency:** the dropdown lists `"Chemyx Nexus 4000"` but the connect code tests for `'Chemyx Nexus 4000X'` (line 459), so that branch may never match. **(maintainer)** These refer to the same pump and should use one name, `Chemyx Nexus 4000`; the code has not yet been changed. |
| `teledyne_pump.py` | Serial driver, class `teledynePump`. | Active | First line is `from msilib.schema import PublishComponent`. `msilib` is a Windows-only standard-library module, and the name imported from it does not appear to be used in this file. Not tested. |
| `milliGAT_pump.py` | Serial driver, class `Milligat` (`set_flow_rate`, `stop_pump`, `aspirate`, `dispense`). | Active | Used for both "MilliGAT LF" and "MilliGAT HF" (selected via a `pump_type` argument). |
| `chemyxFusion4kX.py` | Serial driver, class `ChemyxFusion4kXPump`. | Active | Used for "Chemyx Fusion 4000X" (and for the `'Chemyx Nexus 4000X'` branch). Same layout as the 6kX file but a different API: methods take a pump number `x`. |
| `chemyxFusion6kX.py` | Serial driver, class `ChemyxFusion6kXPump`. | Active | Used for "Chemyx Fusion 6000X". `diff` against the 4kX file shows the class name, constructor, and method signatures differ (e.g. `startPump(self)` vs `startPump(self, x)`). Treat as two drivers, not a copy. |
| `jasco2080.py` | Serial driver, class `JascoPU2080` (start, stop, flow, pressure and pressure-limit read/set). | Active | Also imported directly by `platform_monitor.py`. Its docstring mentions importing "from jasco_pump232"; there is no such file in the repo, and the docstring appears to be a leftover. |

### Valves

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `valveWidget.py` | `ValveControl` widget. Valve types: BioChem 6-way selection, BioChem 8-way selection, BioChem 6-way switching, Rheodyne 2-position switching, Vici 2-position switching. | Active | Chooses the driver class from the type string (lines 303–312). |
| `valve_controller_selection.py` | `selectionValve` serial driver, used for both BioChem selection types. | Active | Its class is also defined inside `valve_controller_switching.py`. |
| `valve_controller_switching.py` | Contains `selectionValve` (same name as above, with an extra `print("Valve homed")`) **and** `switchingValve`. | Active | `valveWidget.py` only uses `switchingValve` from this file. The `selectionValve` copy is not used. |
| `rheodyne232.py` | `rheodyneValve` serial driver (`connect`, `switch`). | Active | |
| `viciValve.py` | `viciValve` serial driver. Docstring warns that if the head is removed the valve must be re-centred with the `LRN` command. | Active | `archive/viciValve_old.py` is an earlier version of this file. |

### Temperature

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `thermocontrollerwidget.py` | `ThermocontrollerControl` widget: connect, set target temperature, read current temperature, safety shutdown. | Active | |
| `thermocontroller_driver.py` | `Furnace` class (Modbus, via `minimalmodbus`). Docstring: "drivers for the Eurotherm 3216", adapted from the `SSJenny90/laboratory` project on GitHub. | Active | |

### Fraction collector

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `fraction_driver.py` | `AzuraFC61` TCP-socket driver (connect, move to vial, move next, collect on/off, position, `drop_count`). Default address `169.254.56.105:10001`. | Active | Also imported by `droplet_calibration.py`. |
| `fraction.ipynb` | Notebook that exercises `AzuraFC61` by hand (connect, identify, status, move, drop count). | Unreferenced | 12 cells. Looks like a manual hardware test; not run. |

## Calibration

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `droplet_calibration.py` | `DropletCounter`: pump flow-rate calibration by counting droplets with the fraction collector; writes CSVs to `calibration_results/`. | Active | Imported lazily from `pumpWidget.py`. It also imports `platformControl` and `pumpWidget` itself, so `pumpWidget` and `droplet_calibration` import each other; `pumpWidget` does its import inside a function. Flowchart: `mermaid_graphs/Droplet_calibration.mmd`. |
| `mass_calibration.py` | `MassBalanceCalibration` and `BalanceSettingsDialog`: pump calibration by mass balance over a serial connection; writes to `calibration_results/`. | Active | Imported lazily from `pumpWidget.py`. Uses `mass_tracker.py`. |
| `mass_tracker.py` | Real-time mass tracker window for A&D HR-A / HR-AZ analytical balances (RS-232C), live plot and CSV streaming. | Active, and Standalone | Its docstring describes it as standalone and it has `main()`. Also imported by `mass_calibration.py`. |
| `calibration_results/` | Output CSVs from the two calibration methods (names such as `calibration_data_<timestamp>.csv`, `droplet_data_<timestamp>.csv`) plus a `Processed Data/` subfolder. | Data / artefact | |

## GPC (gel permeation chromatography) and other analysis

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `GPC_calibration.py` | "GPC calibration" tab: add calibrant runs, fit, save and load a calibration (`.xlsx` via file dialog). | Active | Imports `GPC_handler` and `PicoGPC`. |
| `GPC_runner.py` | "GPC analysis runner" tab: inject, measure, plot, save/load results as `GPCresults_<date>.pkl`. | Active | Imports `GPC_handler` and `PicoGPC`. |
| `GPC_handler.py` | `GPC_handler`: schedules injection with APScheduler, collects and analyses chromatograms. | Active | **Hard-coded path:** loads `C:\Users\Pcubed\miniconda3\envs\P3\Calibration.pkl` (line 152). It will fail on any machine without that exact path. **(maintainer)** `Pcubed` is the name of a desktop computer, not a person. `Calibration.pkl` is legacy, and how `GPC_handler.py` uses it still needs cleaning up; this has not been touched yet. |
| `GPC_handler_test.py` | Variant of `GPC_handler.py`. | Duplicate / variant | Not imported anywhere. `diff` shows 36 differing lines, including: shorter measurement times (330 and 340 vs 900), the valve-sample call commented out, a different `Calibration.pkl` path (`...\P3\P3_SDL\Calibration.pkl`), a lower peak threshold (0.1 vs 0.25), a different elution-time cut-off (320 vs 300), and no handling of a separate UV column in the results. `GPC_handler.py` is the more recent in these respects. Despite the name, the file contains no tests. |
| `PicoGPC.py` | `PicoGPC`: reads the Pico TC-08 over USB in a background thread (the comment says RI signal), saves data. | Active | Imports `tc08usb`. Line 93 saves to a hard-coded `G:\My Drive\Coding\P3_SDL`. |
| `PicoGPC_old.py` | Earlier version of `PicoGPC.py`. | Unreferenced | Same hard-coded save path. |
| `tc08usb.py` | ctypes wrapper for the Pico TC-08 DLL (default DLL path `C:\Program Files\Pico Technology\PicoLog`). | Active | Needs the `six` package (not listed in either env file) and the Pico driver installed. |
| `picoThermocouples.py` | `PicoThermocouples` Qt widget for temperature logging with the TC-08. | Unreferenced | Nothing in the repo imports it. |
| `DLS_handler.py` | `StoppedFlowDLS` widget: stopped-flow dynamic light scattering (sample and scan, get data). | Active (legacy API) | Reached via `conventionalEP.py` → `experimentMethod.py`. Lines 16–17 use `self.main.controller.pump10` and `.valve4`. Reads/writes fixed folders `C:\Users\Pcubed\Documents\Peter\Online-DLS\Data-hold` and `...\Data-save`. |
| `GPCmethoddev_class.ipynb` | Notebook with a draft `GPC_runner` class and plotting. | Unreferenced | 8 cells; appears to be method-development scratch work. |
| `P3_analysisHub.py` | An older "analysis hub" widget combining a conductivity monitor and `PicoGPC`. | Unreferenced | Imports `conductivityMonitor` and `DLS_handler_new`, **neither of which exists in the repo**, so this file cannot be imported as it stands. The name suggests it comes from the earlier "P3" platform. |
| `Calibration.pkl` | GPC calibration data loaded by `GPC_handler.py`. | Legacy (maintainer) | See the `GPC_handler.py` row. |
| `GPCresults_*.pkl` (3 files) | Saved GPC results from May 2025. | Data / artefact | Status not stated by the maintainer. |

## Method builder tab (legacy, to be rebuilt)

**(maintainer)** The Method builder was designed for a legacy build of the platform. It is not currently used and is expected to be rebuilt. It was left in place because it was not clear what else depends on it.

The "Method builder" tab (`experimentMethod.py`) is still created at start-up, so the code is part of the running application even though it is not used. Parts of it appear to be written for an earlier version of the platform control tab:

- `experimentMethod.py` (for example lines 1041–1048 and 1230), `conventionalEP.py` and `DLS_handler.py` use `self.main.controller.pump1`, `pump2`, … `pump10` and `valve1` … `valve4` in live (non-commented) lines. The current `PlatformControl` does **not** define attributes with those names (it keeps `pump_widgets` and `valve_widgets` lists). Calling these code paths would therefore be expected to raise `AttributeError`. This was found by reading the code; it has not been run. The four screener files only mention such names in commented-out lines.
- The optimisation calls are disabled: `# import optimiser` is commented out in `experimentMethod.py`, and the places that used it now set `expDesign = dict()` or `newConditions = dict()` (lines 893, 909, 1297). `OLDexperimentMethod.py` still has the live calls, but there is no `optimiser.py` in the repo.
- `DoEbuilder.py` carries the comment: "legacy code, used in method builder, untouched by Zak - unsure of impact on other files, so not deleted."

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `experimentMethod.py` | `ExperimentMethod`: builds experiment designs (OFAAT, central-composite DoE, screening methods), computes flow rates, starts/stops experiments, sampler cleaning. About 1,300 lines. | Active (legacy API) | See above. Line 518 uses a hard-coded image path under `C:\Users\pm15pmp\...`. |
| `conventionalEP.py` | `conventionalEP`: script that runs a conventional emulsion-polymerisation experiment, reading settings from `main.methodHandler`. | Active (legacy API) | Uses `controller.pump…`/`valve…` names in live lines (see above). Last changed 2026-01-19. |
| `surfactantScreen.py`, `seedAmountScreen.py`, `nFeedsScreen.py`, `monomerScreen.py` | One screening-experiment widget each. | Active | Similar structure. Commented-out lines such as `# self.pumpSeed = self.controller.pump1` show the pump-numbering convention they were written for. Whether they work with the current platform tab was not determined. |
| `flowrateCalculator.py` | `calculateFlowrates(...)`: flow rates from method parameters for the emulsion polymerisation recipes. | Active | |
| `glassTransitionPredictor.py` | Fox-equation glass-transition calculations (`calculateTg`, `calculateComposition`). | Active | |
| `DoEbuilder.py` | `buildCC`: central-composite design via `doepy`. | Active | See the comment quoted above. |
| `OFAATbuilder.py` | `buildOFAAT`: one-factor-at-a-time design. | Active | |
| `Sequence_Builder.py` | `Sequence_builder` Qt widget for editing a sequence table. | Legacy (maintainer) | Nothing imports it. **(maintainer)** It is an older version of the sequence builder that now lives in `platformControl.py`, which has methods with matching names (`add_row`, `remove_selected_rows`, `_get_table_headers`, …). |

## Optimisation and design-of-experiments scripts (not part of the GUI)

| File | What it does | Status | Notes (evidence) |
|---|---|---|---|
| `OLDoptimiser.py` | `getNextExperiment`: multi-objective optimisation step using `summit` (TSEMO). | Unreferenced | Needs `summit`, which is not in either env file. |
| `latinHypercubeSampling.py` | Latin-hypercube experiment sampling via `summit`. | Unreferenced | Its import is commented out in `experimentMethod.py` (`# import latinHypercubeSampling`). Needs `summit`, which is not in either env file. |
| `calculateHypervolume.py` | Script that computes hypervolume for `.xlsx` results in a folder using `pymoo`. | Unreferenced | Folder paths are placeholders (`'insert path to data'`). `pymoo` is not in either env file. |

## Superseded and old versions

| File | What it is | Status | Notes (evidence) |
|---|---|---|---|
| `OLDexperimentMethod.py` | Older copy of `experimentMethod.py`. | Duplicate / variant | `diff` shows 19 differing lines, all about `optimiser` (live in OLD, disabled in current). Not imported. Importing it would fail because `optimiser` does not exist. |
| `Newfiles/platformControl.py` | Older `PlatformControl`. | Duplicate / variant | Its imports are only `PyQt5`, `pumpWidget` and `valveWidget` (the current file also imports the sequence, fraction-collector and config helpers). Python imports the root `platformControl.py`, not this one. |
| `archive/valveWidget_old.py` | Earlier `valveWidget.py`. | Unreferenced | |
| `archive/viciValve_old.py` | Earlier `viciValve.py`. | Unreferenced | Current file adds a `sample()` method and a re-centring note. |

## Environment, documentation and repo housekeeping

| File | What it is | Notes |
|---|---|---|
| `P4_env.yaml` | The conda environment: Python 3.11, numpy 2.0.1, pandas 2.3.3, scipy, PyQt, pyqtgraph, `ax-platform`, `numexpr`, minimalmodbus, apscheduler, pyserial; `pydoe-0.3.8` via pip. | **(maintainer)** The current environment. On 2026-10-23 this file was replaced with the contents of the former `P4_env_v2.yaml` (environment `name:` changed from `P4_env_v2` to `P4_env`), and `P4_env_v2.yaml` was removed. The earlier Python 3.9 version is in git history. It does not list `six` (needed by `tc08usb.py`), `summit` or `pymoo`. Not installed or tested here. |
| `README.md` | Project readme. | Rewritten alongside this file. |
| `TO DO.yaml` | Short to-do note: plot UV chromatogram; DoE tab for the new architecture; handshake/ping for all equipment; "UV off by an order of magnitude". | Kept as the only record of planned work. |
| `Copyright (c) 2026 Zak Pinkney.litcoffee` | Text of an MIT-style permission notice, "Copyright (c) 2026 Zak Pinkney". | The file is named like a licence but is not called `LICENSE`, so tools (and GitHub) will not detect it. |
| `.gitignore` | Ignores `__pycache__/`, `.vscode/`, logs, and `*.xls`, `*.xlsx`, `*.csv`. | Some `.csv` and `.xlsx` files are tracked by git anyway (see below). |
| `.vscode/settings.json` | Sets conda as the default environment/package manager in VS Code. | |
| `mermaid_graphs/` | Two Mermaid flowcharts: `sequence_manager.mmd`, `Droplet_calibration.mmd`. | Generated documentation of those two modules. |
| `graphify-out/` | Output of the `graphify` tool (knowledge-graph of the code). | 63 files tracked in git. A commit message reads "added graphify file to help understanding of code logic and graphically demonstrate p4". Generated; may go stale. |
| `__pycache__/` | Python bytecode. | Ignored by git. |

## Data files in the repo

Several of these are tracked in git even though `.gitignore` excludes `*.csv`/`*.xlsx`.

| Item | Notes |
|---|---|
| `Experimental_logs/` (46 CSVs in the working folder, 20 of them tracked by git) | Output of `platform_monitor.py`. File names are dated 2026-02-12 to 2026-08-31. |
| `calibration_results/` | Output of the two pump-calibration methods (see above). |
| `Calibration_s.xlsx`, `Current_Calibration.xlsx`, `calib20225.xlsx`, `calib_data.xlsx`, `calib_data.csv`, `calibration_0207.xlsx`, `calibration_0207.csv` | **(maintainer)** Legacy calibration files in the repository root. Despite the name, `Current_Calibration.xlsx` is not current. |
| `testn.xlsx` | Not covered by the maintainer's answer; role **Unknown**. |
| `~$calibration_0207.xlsx` | An Excel lock file (created while the workbook was open). It has no content of value. |

---

## Maintainer answers

Recorded 2026-10-23, from the maintainer's replies to the questions first listed in this file.

| # | Question | Answer |
|---|---|---|
| 1 | Is the Method builder expected to work on the current platform? | No. It was designed for a legacy build, is not currently used, and is expected to be rebuilt. It was left in place because its dependencies were unclear. |
| 2 | Which environment file is current? | `P4_env_v2.yaml`, which has since replaced `P4_env.yaml` (done). |
| 3 | Which calibration files are current? | None of the files in the repository root. `Calibration.pkl` and the calibration spreadsheets are legacy. How `GPC_handler.py` uses `Calibration.pkl` needs cleaning but has not been touched. `Pcubed` in the hard-coded paths is the name of a desktop computer. |
| 4 | Is `Sequence_Builder.py` older or newer than the sequence table in `platformControl.py`? | Older, legacy. |
| 5 | Is anything outside the repo using the unreferenced files? | No, for `picoThermocouples.py`, `PicoGPC_old.py`, `OLDoptimiser.py`, `latinHypercubeSampling.py` and `calculateHypervolume.py`. |
| 6 | Is the `Chemyx Nexus 4000` / `4000X` mismatch intentional? | No: the names refer to the same pump and should be the single name `Chemyx Nexus 4000`. |
| 7 | Does the application start with no hardware? | Yes, but it does not do much. |
| 8 | Which licence is intended? | Not known. |

## Still open

1. **Why the Method builder uses `pump1…pump10` and `valve1…valve4`.** The maintainer was unsure of their relevance. The current `PlatformControl` keeps pumps and valves in lists (`pump_widgets`, `valve_widgets`) and defines no attributes with those names; why the Method builder expects them is not known. Resolve this when the Method builder is rebuilt.
2. **Licence.** The notice in the repo is MIT-style (see above), but the maintainer does not know which licence is intended. A licence needs to be chosen and the file renamed to `LICENSE`.
3. **`testn.xlsx`**, and whether the three `GPCresults_*.pkl` files are still needed.
4. **Cleanup actions agreed but not carried out:** unify the Chemyx Nexus 4000 name in `pumpWidget.py`; clean the `Calibration.pkl` handling in `GPC_handler.py`; decide what to do with the legacy files confirmed above.
