Version of P4 currently being developed by Zak; no changes to this code are permitted, only forking, if you have changes you want implimented, create a pull request 

used in case of major errors.

Code for running the MainWindow of the PCubed GUI New tabs are added here, with each tab taking the argument 'main=self' so the same objects can be called from one tab to another. In this way, for example, commands can be sent from the method handler to the platform controller, and equally objects in the controller can send information back to the method handler

MainWindow is best run in full screen, which it will automatically open in

Created in Python 3.9.0

Peter Pittaway 2023 University of Leeds

In order to run this, you can create a conda environment from p3_env.yaml. in your shell (like conda, or powershell) or vs code terminal, use: conda env create -f p3_env.yaml (after you have forked the repository into your own github, then git cloned the URl found unde the 'code' button in green this will create a new environment with all the required packages, which will save you some time first setting up the system.
