from apscheduler.schedulers.background import BackgroundScheduler
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
import threading
from zoneinfo import ZoneInfo

# Uncomment line 76 when valve connected
class GPC_handler(QObject):
    GPC_complete = pyqtSignal(dict)
    # Standard initiation, also pass a PicoGPC object in, which gives access to the RI signal
    def __init__(self, parent, main, PicoGPC):
        super().__init__() 
        self.main = main
        self.iter = 0
        self.GPCResults = None
        uk_timezone = ZoneInfo("Europe/London")
        
        self.GPCscheduler = BackgroundScheduler(timezone=uk_timezone)
        self.event = threading.Event()
        self.RealTime = [datetime.now()] * 3
        self.PicoGPC = PicoGPC
        self.GPCValve = self.main.controller.valve5
        self.PicoGPC.dataReady.connect(self.import_data)

    # Start a thread for GPC - either for analysis (default) or for a calibration
    def GPC_start(self, type='default', injnum=1, sampleID=None):
        print("GPC start")
        if type == 'default':
            self.injnum = injnum
            self.sampleID = sampleID
            GPC_Thread = threading.Thread(target=self.GPC_run)
            GPC_Thread.start()
        elif type == 'calibrant':
            calib_Thread = threading.Thread(target=self.calibrant_run)
            calib_Thread.start()

    # Initialise a calibrant run, and then return results via signal to GPC_calibration tab in GUI
    def calibrant_run(self):
        print("GPC calibrant triggered")
        self.GPC_calibrant_inject()
        self.event.wait()
        print("completed", datetime.now())
        calib_data  = self.GPCdata
        StartTime = self.InjectionTime
        print(StartTime)
        self.calibResults = self.calib_analysis(calib_data, StartTime)
        self.GPC_complete.emit(self.calibResults)
    # Initialise a triple injection GPC run, and then return results via signal to GPC_calibration tab in GUI
    def GPC_run(self):
        print("GPC triggered!")
        if self.injnum==3:
            self.iter = 0
            self.GPCscheduler.add_job(self.GPC_inject, trigger='interval', seconds=175, id='GPC_inject')
            self.GPCscheduler.start()
        self.GPC_inject()
        self.event.wait()
        # Change to commented
        # Check if GPCdata exists and if so, use it
        if hasattr(self, 'GPCdata'): 
            GPCdata = self.GPCdata
        
            StartTime = [rt if isinstance(rt, datetime) else datetime.now() for rt in self.RealTime]
            print('RealTime', self.RealTime)
            self.GPCResults = self.GPC_analysis(GPCdata, StartTime)
            print("GPC completed! Results =")
            print(f"{self.GPCResults['Averages']}") 
            
            self.GPC_complete.emit(self.GPCResults)
        print("all done")

    # Calibrant Injection; start monitoring RI signal
    def GPC_calibrant_inject(self):
        # set measurement time in seconds
        meas_time = 330
        # Print start and end times, and set them in GUI on appropriate QLabels
        print("Injection number", str(self.iter+1), "time=", datetime.now().strftime("%H:%M:%S"))
        self.main.GPC_calibration.start_time.setText(datetime.now().strftime("%H:%M:%S"))
        print("Expected end time =", (datetime.now() + timedelta(seconds=meas_time)).strftime("%H:%M:%S"))
        self.main.GPC_calibration.end_time.setText((datetime.now() + timedelta(seconds=meas_time)).strftime("%H:%M:%S"))
        self.InjectionTime = datetime.now()
        # Injection via valve object
        self.GPCValve.valveSample()
        print("self.Picomeasure")
        # Monitor RI signal for measurement time
        self.PicoGPC.measure(meas_time)
        # threading.Timer(3, self.delayed_return).start() #3s delay

    def GPC_inject(self):
        if self.injnum == 3:
            meas_time = 700
        else:
            meas_time = 340
        if self.iter == 0:
            self.main.GPC_runner.start_time.setText(datetime.now().strftime("%H:%M:%S"))
            self.main.GPC_runner.end_time.setText((datetime.now() + timedelta(seconds=meas_time)).strftime("%H:%M:%S"))
            self.PicoGPC.measure(meas_time)
        print("Injection number", str(self.iter+1), "time=", datetime.now().strftime("%H:%M:%S"))
        # Sample valve each time inject runs
        
        ######CHANGE TO ACTUALLY SAMPLE VALVE#######
        
        self.GPCValve.valveSample()
        self.RealTime[self.iter] = datetime.now()
        self.iter +=1
        if self.iter >= 3:
            self.GPCscheduler.remove_job('GPC_inject')
            # Change this to the start time thing
            # threading.Timer(3, self.delayed_return).start() #3s delay

    def import_data(self, data):
        print("Importing data")
        ## Uncomment these when attached to TC08
        self.GPCdata = data
        print(self.GPCdata)
        self.event.set()
        # self.delayed_return(self)
    
    def delayed_return(self):
        print("Data collected")
        self.event.set()  # Unblocks the waiting function
    

    def GPC_analysis(self,GPCresults, StartTime):
        chromlength = 800
        
        # Define detection limit for Peak filtering
        detectlimit = 7
        injnum = self.injnum
        # Initialise Results dictionary and other storage arrays
        chrom = np.zeros((chromlength,6))
        polpeak = pd.DataFrame()

        Results = {"rawchrom": GPCresults,
                "Mn": np.zeros(injnum),
                "Mw": np.zeros(injnum),
                "PD": np.zeros(injnum),
                "MP": np.zeros(injnum),
                "chrom": [],
                "polpeak": [],
                "StartTime": StartTime,
                "Averages":[],
                "injnum": self.injnum,
                "sampleID": self.sampleID,
                }

        # Load calibration polynomial
        with open(r'C:\Users\Pcubed\miniconda3\envs\P3\Calibration.pkl', 'rb') as f:
            poly = pickle.load(f)

        #Convert GPC results to arrays
        if "RI" in GPCresults.columns:
            elution_time = GPCresults["Time"].to_numpy()
            RI_signal = GPCresults["RI"].to_numpy()
            uv_signal = GPCresults["UV"].to_numpy() if "UV" in GPCresults.columns else None
        else:
            elution_time, RI_signal = GPCresults.to_numpy().T
            uv_signal = None
        #Add start time manipulation (see MATLAB)
        #Points on baseline (ADJUST after calibration)

        fitpoints = (
            (elution_time > 0) & (elution_time < 110) |
            (elution_time > 279) & (elution_time < 282) |
            (elution_time > 450) & (elution_time < 453) |
            (elution_time > 680)
        )

        # Fit polynomial to baseline
        baseline = np.polyfit(elution_time[fitpoints], RI_signal[fitpoints], 1)
        # Subtract baseline
        RI_signal -= np.polyval(baseline, elution_time)

        indices = []
        for rt in StartTime:
            # Find the closest index in the elution_time array for each StartTime
            rt_seconds = (rt - StartTime[0]).total_seconds()
            time_diffs = np.abs(elution_time - rt_seconds)
            closest_index = np.argmin(time_diffs)
            indices.append(closest_index)

        for i in range(injnum):
            start_idx = indices[i]
            end_idx = start_idx + chromlength
            
            
            
            # Define region of interest (i.e. chromatogram) for analysis in each loop & filter
            elution_time_ana = elution_time[start_idx:end_idx]
            RI_signal_ana = RI_signal[start_idx:end_idx]
            # Make elution_time_ana start at 0
            elution_time_ana = elution_time_ana - elution_time_ana[0]

            # Filter for data between min and max calibrant elution
            peakfilter = ((elution_time_ana > 122) & (elution_time_ana < 201))
            peakdata = RI_signal_ana[peakfilter]
            peaktime = elution_time_ana[peakfilter]

            # Check if peak exists - if not, set penalty values
            if max(peakdata) < 0.25:
                PD = 3
                MP = 0
                Mn = 0
                Mw = 0
                chrom[:,2*i] = elution_time_ana
                chrom[:,2*i+1] = RI_signal_ana
                # polpeak = 0
            else:
                # Normalise peak data
                peakdata = peakdata/max(peakdata)
                # Set detection limit relative to peak height and eliminate data below threshold
                peakfilter = peakdata > max(peakdata)/detectlimit
                peakdata = peakdata[peakfilter]
                peaktime = peaktime[peakfilter]
                # Convert time scale to MW using calibration polynomial
                M1 = poly[0]*peaktime**3
                M2 = poly[1]*peaktime**2
                M3 = poly[2]*peaktime
                M4 = poly[3]
                MWData = M1+M2+M3+M4
                MWData = 10**MWData
            
                # Calculate number average molecular weight
                Mn = sum(peakdata*MWData)/sum(peakdata)
                Mw = sum(peakdata*MWData**2)/sum(peakdata*MWData)
                PD = Mw/Mn
                # Find location of peak maximum 
                MP = MWData[np.argmax(peakdata)]
                # Store chromatogram data
                chrom[:,2*i] = elution_time_ana
                chrom[:,(2*i)+ 1] = RI_signal_ana
                # Store polynomial peak data
                newpolpeak = pd.DataFrame([MWData,peakdata]).T
                polpeak = pd.concat([polpeak,newpolpeak],axis=1).fillna(0)
            # Store results in Results dict:
            Results["Mn"][i] = Mn
            Results["Mw"][i] = Mw
            Results["PD"][i] = PD
            Results["MP"][i] = MP
            
        Results["chrom"] = pd.DataFrame(chrom)
        if uv_signal is not None:
            Results["rawchrom"] = pd.DataFrame(GPCresults, columns=["Time", "RI", "UV"])
        else:
            Results["rawchrom"] = pd.DataFrame(GPCresults, columns=["Time", "Signal"])
        Results["polpeak"] = polpeak
        Results["Averages"] = pd.DataFrame([[np.mean(Results["Mn"]), np.mean(Results["Mw"]), np.mean(Results["PD"]), np.mean(Results["MP"])]], columns=["Mn", "Mw", "PD", "MP"])

        return Results



    



    def calib_analysis(self, calib_data, StartTime):
        chromlength = 800
        # Initialise Results dictionary and other storage arrays
        chrom = np.zeros((chromlength,2))
        Results = {"rawchrom": calib_data,
                "chrom": [],
                "StartTime": StartTime,
                "max_elution_time":[],
                }


        #Convert GPC results to two separate arrays
        if "RI" in calib_data.columns:
            elution_time = calib_data["Time"].to_numpy()
            RI_signal = calib_data["RI"].to_numpy()
        else:
            elution_time, RI_signal = calib_data.to_numpy().T
        elution_time = elution_time[0:chromlength]
        RI_signal = RI_signal[0:chromlength]
        #Add start time manipulation (see MATLAB)
        #Points on baseline (ADJUST after calibration)
        fitpoints = (
            (elution_time > 0) & (elution_time < 80) |
            (elution_time > 300) # not this was 320 before i changed JG - check it 
        )
        # fitpoints = (
        #             (elution_time > 0) & (elution_time < 2) |
        #             (elution_time > 10)
        #         )

        # Fit polynomial to baseline
        baseline = np.polyfit(elution_time[fitpoints], RI_signal[fitpoints], 1)
        # Subtract baseline
        RI_signal -= np.polyval(baseline, elution_time)
        # Find location of peak max for calibrant elution time
        max_index = np.argmax(RI_signal)
        # Get the elution time of the maximum peak
        Results["max_elution_time"] = elution_time[max_index]
        # Store chrom
        chrom[:,0] = elution_time
        chrom[:,1] = RI_signal
        Results["chrom"] = chrom

        return Results

