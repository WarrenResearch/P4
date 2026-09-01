# Graph Report - P4_SDL  (2026-09-01)

## Corpus Check
- Corpus is ~41,249 words - fits in a single context window. You may not need a graph.

## Summary
- 643 nodes · 909 edges · 44 communities (13 shown, 24 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.87)
- Token cost: 33,900 input · 2,505 output

## Community Hubs (Navigation)
- Pico Data Acquisition & Thermocouples
- Experiment Screens & DoE Builders
- Furnace Temperature Controller Driver
- Main GUI & Platform Orchestration
- Droplet Counter & Pump Calibration
- PlatformControl Fraction Collector & Sequencing
- Chemyx Fusion 4kX Pump Driver
- Chemyx Fusion 6kX Pump Driver
- Azura FC61 Fraction Collector Driver
- Platform Monitor & Logging
- Experiment Method Workflow
- Legacy Experiment Method
- Jasco PU2080 HPLC Pump Driver
- GPC Calibration UI
- GPC Runner UI
- Thermocontroller Widget
- Valve Control Widget
- Sequence Executor
- Fraction Collector Handler
- GPC Handler (Test Variant)
- Archived Valve Widget
- GPC Handler
- Selection Valve Controller
- Project Environment & Architecture Docs
- Switching Valve Controller
- milliGAT Pump Driver
- Sequence Builder UI
- VICI Valve Driver
- Archived VICI Valve Driver
- PlatformControl Sequence Targets Upload
- Newfiles PlatformControl Variant
- Rheodyne 232 Valve Driver
- Switching Valve Class
- Latin Hypercube Sampling
- Legacy Optimiser
- PlatformControl Monitor Start Time
- UV Chromatogram TODOs

## God Nodes (most connected - your core abstractions)
1. `PlatformControl` - 58 edges
2. `Furnace` - 25 edges
3. `ChemyxFusion4kXPump` - 24 edges
4. `ChemyxFusion6kXPump` - 24 edges
5. `ExperimentMethod` - 19 edges
6. `ExperimentMethod` - 19 edges
7. `JascoPU2080` - 18 edges
8. `PumpControl` - 18 edges
9. `TC08USB` - 18 edges
10. `SequenceExecutor` - 17 edges

## Surprising Connections (you probably didn't know these)
- `doepy (DOE library)` --semantically_similar_to--> `pydoe (DOE library)`  [INFERRED] [semantically similar]
  P4_env.yaml → P4_env_v2.yaml
- `PlatformControl` --uses--> `FractionCollectorHandler`  [INFERRED]
  platformControl.py → fraction_collector_handler.py
- `PlatformControl` --uses--> `PlatformConfigHandler`  [INFERRED]
  platformControl.py → platform_config.py
- `PlatformControl` --uses--> `SequenceExecutor`  [INFERRED]
  platformControl.py → sequence_manager.py
- `PicoGPC` --uses--> `TC08USB`  [INFERRED]
  PicoGPC.py → tc08usb.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **main=self Cross-Tab Communication Pattern** — readme_pcubed_gui, readme_tab_architecture, readme_method_handler, readme_platform_controller [EXTRACTED 0.75]

## Communities (44 total, 24 thin omitted)

### Community 0 - "Pico Data Acquisition & Thermocouples"
Cohesion: 0.06
Nodes (11): Enum, analysisHub, PicoGPC, PicoGPC, QObject, PicoThermocouples, object, TC08USB (+3 more)

### Community 1 - "Experiment Screens & DoE Builders"
Cohesion: 0.05
Nodes (6): conventionalEP, StoppedFlowDLS, monomerScreener, nFeedsScreener, seedAmountScreener, surfactantScreener

### Community 2 - "Furnace Temperature Controller Driver"
Cohesion: 0.07
Nodes (22): connect(), Furnace, get_ports(), Contains the drivers for the Eurotherm 3216 Code inspired from…, If heat_rate is specified, this method sets the heating rate of the furnace. If…, [Query only] Queries the current temperature of furnace. :returns: Temperature…, Resets the current timer and immediately restarts. Used in for loops to reset…, If temperature is specified, this method sets the target temperature of… (+14 more)

### Community 3 - "Main GUI & Platform Orchestration"
Cohesion: 0.09
Nodes (5): mainWindow, Code for running the MainWindow of the PCubed GUI New tabs are added here, with…, PlatformConfigHandler, object, teledynePump

### Community 4 - "Droplet Counter & Pump Calibration"
Cohesion: 0.10
Nodes (5): DropletCounter, PumpControl, any, Read current flow rate from pump. Returns flow in mL/min or 0.0 if not…, Read current pressure from pump. Returns pressure in bar or 0.0 if not…

### Community 6 - "Chemyx Fusion 4kX Pump Driver"
Cohesion: 0.12
Nodes (4): ChemyxFusion4kXPump, parsePortName(), object, On macOS and Linux, selects only usbserial options and parses the 8 character…

### Community 7 - "Chemyx Fusion 6kX Pump Driver"
Cohesion: 0.12
Nodes (4): ChemyxFusion6kXPump, parsePortName(), object, On macOS and Linux, selects only usbserial options and parses the 8 character…

### Community 8 - "Azura FC61 Fraction Collector Driver"
Cohesion: 0.10
Nodes (14): AzuraFC61, Establishes a TCP/IP connection to the device., Closes the connection., Returns general device information[cite: 448]., Sets the instrument to REMOTE mode to lock GUI input[cite: 452]. priority 1 =…, Unlocks GUI keyboard and returns to LOCAL mode[cite: 456]., Returns the full status string of the device[cite: 57]., Initializes the driver for Ethernet communication. (+6 more)

### Community 9 - "Platform Monitor & Logging"
Cohesion: 0.12
Nodes (11): PlatformMonitor, Get pump list from Platform Control. Returns list of pump widgets or empty list., Create/recreate pump-specific plot curves based on current pump_names., Load pump configuration from Platform Control and initialize plots., Read temperature with retry logic to avoid transient Modbus failures., Update timer interval from UI value in seconds., Append latest values to buffers and refresh all plot curves. Args: now:…, Live plotting + periodic CSV logging for key platform process variables. (+3 more)

### Community 15 - "Thermocontroller Widget"
Cohesion: 0.19
Nodes (6): Update available COM ports in the combo box, Connect to the thermocontroller on the selected COM port, Disconnect from the thermocontroller, Set the target temperature on the thermocontroller, Update the current temperature display from the thermocontroller, ThermocontrollerControl

### Community 23 - "Project Environment & Architecture Docs"
Cohesion: 0.25
Nodes (11): doepy (DOE library), P4_env Conda Environment, Ax Platform, P4_env_v2 Conda Environment, pydoe (DOE library), Method Handler, PCubed GUI MainWindow (P4), Platform Controller (+3 more)

### Community 25 - "milliGAT Pump Driver"
Cohesion: 0.25
Nodes (3): Milligat, The flow rate is given in mL/min. The pump type should be either 'HF': High…, Creates a controller for the MilliGat pumps Args: name: The name of the pump…

### Community 27 - "VICI Valve Driver"
Cohesion: 0.22
Nodes (3): object, if you have taken the head off the switching valve for any reason you must use…, viciValve

## Knowledge Gaps
- **3 isolated node(s):** `Plot UV Chromatogram`, `Equipment Handshake/Ping`, `UV Reading Off By Order of Magnitude`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 278 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PlatformControl` connect `PlatformControl Fraction Collector & Sequencing` to `PlatformControl Sequence Row Styling`, `PlatformControl Sequence Targets Upload`, `Main GUI & Platform Orchestration`, `PlatformControl Monitor Start Time`, `PlatformControl Run Sequence`, `PlatformControl Timer Scheduling`, `Sequence Executor`, `Fraction Collector Handler`, `PlatformControl Sample Definitions`, `PlatformControl Pump Table Setup`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `AzuraFC61` connect `Azura FC61 Fraction Collector Driver` to `Main GUI & Platform Orchestration`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `PlatformControl` (e.g. with `FractionCollectorHandler` and `PlatformConfigHandler`) actually correct?**
  _`PlatformControl` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Plot UV Chromatogram`, `Equipment Handshake/Ping`, `UV Reading Off By Order of Magnitude` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pico Data Acquisition & Thermocouples` be split into smaller, more focused modules?**
  _Cohesion score 0.06108597285067873 - nodes in this community are weakly interconnected._
- **Should `Experiment Screens & DoE Builders` be split into smaller, more focused modules?**
  _Cohesion score 0.05217391304347826 - nodes in this community are weakly interconnected._
- **Should `Furnace Temperature Controller Driver` be split into smaller, more focused modules?**
  _Cohesion score 0.0696969696969697 - nodes in this community are weakly interconnected._