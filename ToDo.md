**listed below is the requirements, strategy, and some context on the things we would like from this platform**


**context** 
this code is designed to control an automated reactor platform. the barebones of every reactor is a pump. this pump can be controlled via this code by itself. additional complexity involves including temperature controllers, samplers, additional pumps, analysis techniques, sequences (including but not limited to DoE) and finally Algorithms - which will take information supplied by analysis techniques (or input yourself) and decide the next conditions to explore.


**strategy**

the main aim is a modular platform that can be easily edited by chemists (crap coders) to add functionality. but keep things relatively straightforeward where possible.

the core function should be a pump, individually controlled (set flowrates in app) and an input for the reactor volume (you could input residence time requirement, pumps then automatically calculate flowrates) pump calibration is required too (manual, automated (fraction collector, mass balance)).

functionality which can be modular

- additional pumps to be controlled 
- temperature controller/ furnace
- detectors (most use picologgers for a direct voltage output, some, like the mass balance take RS232 output, some use direct connection through Ethernet cable, most are called through COMXX)
- sequences (add pump flowrates, temperature control, relative flowrates etc)

the ability to customise and add functionality is the aim - so platform specifics 