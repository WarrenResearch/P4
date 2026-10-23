# P4 SDL: automated flow-reactor control software

Python/Qt (PyQt5) desktop application for controlling an automated flow reactor platform: pumps, valves, a thermocontroller, a fraction collector and online GPC measurement, with a sequence table that steps the platform through a series of experimental conditions and logs the results.

The application is a single window (`_Main_GUI.py`) with five tabs. The code descends from the earlier "P3" platform (Peter Pittaway, University of Leeds, 2023, per the header of `_Main_GUI.py`); this repository is the P4 version, developed by Zak Pinkney.

> **Status of this documentation.** The documentation in this repo was written by reading the code. The application has not been run as part of writing it, and several parts of the code are old or only partly connected. Where something is uncertain, the docs say so. Start with [docs/FILE_STATUS.md](docs/FILE_STATUS.md).

## Where to start

| If you want to… | Read |
|---|---|
| Know which files matter and which are old, duplicated or broken | [docs/FILE_STATUS.md](docs/FILE_STATUS.md) |
| See what the application does and which hardware it supports | [What is in the application](#what-is-in-the-application) and [Supported devices](#supported-devices) below |
| Find the things that are known to be wrong or unfinished | [Known problems](#known-problems) below, and `TO DO.yaml` |

Planned documents that do not exist yet: architecture overview, how to add a device, platform configuration reference, hardware catalogue, development guide.

## What is in the application

Run `_Main_GUI.py` and the main window opens maximised with these tabs:

| Tab | What it is for | Code |
|---|---|---|
| **Method builder** | **Legacy; not currently used and due to be rebuilt.** Designs a set of experiments (one-factor-at-a-time, central-composite DoE, screening methods) and calculates flow rates. It was written for an older platform build; see [Known problems](#known-problems). | `experimentMethod.py` and the files it imports |
| **Platform control** | Add pumps, valves and a thermocontroller; connect to them; set flow rates and temperature; define a sequence table of conditions; define samples and reactor volumes; operate the fraction collector; calibrate pumps; save and load the platform layout. | `platformControl.py` |
| **GPC calibration** | Build a GPC calibration from calibrant runs (fit, save and load). | `GPC_calibration.py` |
| **GPC analysis runner** | Inject and measure GPC samples, plot chromatograms, save results (Excel and pickle) and load saved GPC data. | `GPC_runner.py` |
| **Platform Monitor** | Live plots of temperature and pump flow/pressure, with each run logged to a CSV in `Experimental_logs/`. | `platform_monitor.py` |

Every tab is constructed as `Tab(parent, main=self)`: each receives the main window as `main`, which is how one tab reaches objects in another (for example, the Platform Monitor reads the pumps held by Platform control).

### Running a sequence (as implemented in the code)

In the Platform control tab, a sequence is a table with a row per set of conditions. `sequence_manager.py` (`SequenceExecutor`) works through the rows: set the row's target temperature and wait for it to be reached, run a wash step, apply the row's flow rates, then sample. A flowchart is in [`mermaid_graphs/sequence_manager.mmd`](mermaid_graphs/sequence_manager.mmd). Sampling uses the fraction collector and the reactor-volume and fraction-delay-volume settings.

## Supported devices

As found in the code (drivers exist and are selectable in the GUI). Nothing here has been verified against real hardware by the author of these docs.

| Kind | Models selectable in the GUI | Driver files |
|---|---|---|
| Pumps | Teledyne; MilliGAT LF; MilliGAT HF; Chemyx Nexus 4000; Chemyx Fusion 6000X; Chemyx Fusion 4000X; Jasco PU2080 | `teledyne_pump.py`, `milliGAT_pump.py`, `chemyxFusion4kX.py`, `chemyxFusion6kX.py`, `jasco2080.py` (wired up in `pumpWidget.py`) |
| Valves | BioChem 6-way selection; BioChem 8-way selection; BioChem 6-way switching; Rheodyne 2-position switching; Vici 2-position switching | `valve_controller_selection.py`, `valve_controller_switching.py`, `rheodyne232.py`, `viciValve.py` (wired up in `valveWidget.py`) |
| Thermocontroller | Eurotherm 3216 (Modbus) | `thermocontroller_driver.py`, `thermocontrollerwidget.py` |
| Fraction collector | Azura FC 6.1 (`AzuraFC61`, TCP socket) | `fraction_driver.py`, `fraction_collector_handler.py` |
| Balance (for pump calibration) | A&D HR-A / HR-AZ series, RS-232 | `mass_calibration.py`, `mass_tracker.py` |
| GPC signal acquisition | Pico TC-08 USB data logger | `PicoGPC.py`, `tc08usb.py` (needs the Pico driver DLL) |

The set of devices on a given platform is stored in `platform_layout.json` (written and read by `platform_config.py`).

## Getting started

These steps come from the previous README and the environment files. The environment file has not been installed or tested by the author of these docs.

1. Fork the repository, then clone your fork.
2. Create the conda environment from `P4_env.yaml` (Python 3.11, numpy 2.0.1):

   ```bash
   conda env create -f P4_env.yaml
   ```

   This file replaced an older Python 3.9 version, which is still in git history. It does not list every package the code imports (for example `six` for `tc08usb.py`); see [docs/FILE_STATUS.md](docs/FILE_STATUS.md).
3. Run the application from the repository root (some output folders, such as `Experimental_logs/` and `calibration_results/`, are created relative to the current directory):

   ```bash
   python _Main_GUI.py
   ```

   The window is intended to be used full screen and opens maximised.

According to the maintainer, the application starts with no hardware connected, but it does little without devices.

## Output files

| Output | Written by | Location |
|---|---|---|
| Run log (one CSV per run, named `Experimental_log_<timestamp>.csv`) | Platform Monitor | `Experimental_logs/` |
| Pump calibration data | droplet-counter and mass-balance calibrations | `calibration_results/` |
| Pump calibration history | `pumpWidget.py` | `calibration_history.json` next to the source |
| Platform layout | `platform_config.py` | `platform_layout.json` next to the source |
| GPC results | GPC analysis runner (save button) | An Excel file at the location chosen in the save dialog, plus a `GPCresults_<timestamp>.pkl` in the same folder |

## Known problems

Found by reading the code (see [docs/FILE_STATUS.md](docs/FILE_STATUS.md) for the evidence and line references):

- **Method builder tab is legacy.** The maintainer confirms it was designed for an older build, is not in use, and is to be rebuilt. `experimentMethod.py`, `conventionalEP.py` and `DLS_handler.py` refer to `main.controller.pump1 … pump10` and `valve1 … valve4`, which the current `PlatformControl` does not define. The optimiser calls in `experimentMethod.py` are disabled (replaced by empty `dict()`s). `TO DO.yaml` lists adapting the DoE code to the new architecture.
- **Hard-coded paths** to a specific lab computer (`Pcubed` is the name of a desktop): `GPC_handler.py` (`C:\Users\Pcubed\miniconda3\envs\P3\Calibration.pkl`), `PicoGPC.py` (`G:\My Drive\Coding\P3_SDL`), `DLS_handler.py` and `experimentMethod.py`. `Calibration.pkl` itself is legacy; how `GPC_handler.py` uses it still needs cleaning.
- **Old and duplicate files** live alongside the active ones (`OLD*.py`, `PicoGPC_old.py`, `GPC_handler_test.py`, `Sequence_Builder.py`, `Newfiles/`, `archive/`, and the calibration spreadsheets in the repository root), and some files import modules that are not in the repo (`P3_analysisHub.py`, `OLDexperimentMethod.py`). The maintainer confirms the calibration spreadsheets, `Sequence_Builder.py` and `Calibration.pkl` are legacy.
- **Naming inconsistency:** the Chemyx Nexus 4000 pump is called `Chemyx Nexus 4000` in the dropdown and `Chemyx Nexus 4000X` in the connect code in `pumpWidget.py`; they should be the same name.
- **Open items** from `TO DO.yaml`: plot the UV chromatogram; a DoE tab in the new architecture; a handshake/ping for all equipment before any process starts; "UV off by an order of magnitude".
- **No automated tests.**

## Contributing

From the previous README: this is the version of P4 currently being developed by Zak; no direct changes are permitted. If you have changes you want implemented, fork the repository and create a pull request. There is no written style guide or branching convention.

## Licence

`Copyright (c) 2026 Zak Pinkney.litcoffee` contains an MIT-style permission notice. The file is not named `LICENSE`, so GitHub will not display it as the project licence. The intended licence has not been decided.
