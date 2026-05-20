import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import time
import fraction_driver
import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np


class DropletCounter:
    def __init__(self):
        #self.driver = fraction_driver.AzuraFC61()
        #self.driver.connect() #initiate connection to the device
        #time.sleep(1) # give it a moment to connect before sending commands
        #self.driver.set_remote(0) #set the fraction collector to remote 
        #time.sleep(0.5) # give it a moment to switch modes before starting to poll
        #self.driver.move_to_vial('C7') # move to the waste vial to start with a clean slate
        #time.sleep(2) # give it a moment to move before starting to poll
        #self.driver.set_collect(1) # make sure collection is off to start with
        
        self.current_run = 1
        self.total_runs = 3

        self.maximum_duration_min = 0.51 # change this for duration of experiment in mins
        self.maximum_duration_s = self.maximum_duration_min * 60

        self.timer = QTimer() 
        self.timer.timeout.connect(self.poll_droplet_count) 
        
        self.master_data = {} # start dictionary with all data
        

        self.start_new_run()

    def start_new_run(self):
        print(f'Starting Calibration Run... {self.current_run} of {self.total_runs}')

        self.start_time = time.time()
        self.start_count = 0 #int(self.driver.drop_count()) # get the starting droplet count from the hardware

        self.droplet_count = []
        self.timestamps = []

        self.timer.start(5000) # poll every 5 seconds

        
    def get_droplet_count(self):
        import random

        if not hasattr(self, '_fake_hardware_count'):
            self._fake_hardware_count = 0
        
        self._fake_hardware_count += random.randint(0, 5) # simulate 0-5 droplets every poll
        return self._fake_hardware_count #int(self.driver.drop_count()) 
    
    
    def poll_droplet_count(self):

        current_time = time.time()
        duration = current_time - self.start_time 
        if duration >= self.maximum_duration_s:
            self.timer.stop()

            gradient_value = self.results_gradient()

            if "Time (s)" not in self.master_data:
                self.master_data["Time (s)"] = self.timestamps

            self.master_data[f'Run {self.current_run} Droplet Count'] = self.droplet_count
            self.master_data[f'Run {self.current_run} Gradient'] = [gradient_value] * len(self.timestamps)


            if self.current_run < self.total_runs:
                self.current_run += 1
                self.start_new_run()
            else:
                self.save_master_csv()
                print('Finished all runs, master CSV saved.')
                QApplication.quit() # Exit the application after saving the CSV
            return
        
        relative_count = self.get_droplet_count() - self.start_count
        
        self.droplet_count.append(relative_count)   
        self.timestamps.append(duration)

        print(f"[Run {self.current_run}] Time: {duration}s, Droplet Count: {relative_count}")

   
    def results_gradient(self):
        #placeholder: this function will take each dataset and find the gradient for each, given y is forced through 0, this is the calibration for each pump
        x = np.array(self.timestamps + [0]) # gives a 0, 0 point for forcing through 0
        y = np.array(self.droplet_count + [0])

        x = x[:,np.newaxis]
        a, _, _, _ = np.linalg.lstsq(x,y,rcond=None)

        print(a)
        return a
    
    def save_master_csv(self):
        results_dir = 'calibration_results'
        os.makedirs(results_dir, exist_ok=True)

        timestamp_str = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(results_dir, f'calibration_data_{timestamp_str}.csv')

        df = pd.DataFrame(self.master_data).to_csv(filepath, index=False,float_format='%.3f')
        print(f'Master CSV saved to: {filepath}')





if __name__ == "__main__":
    app = QApplication(sys.argv)

    tracker = DropletCounter()

    try:
        sys.exit(app.exec_()) 
    except KeyboardInterrupt:
        tracker.timer.stop()
        if tracker.master_data:
            tracker.save_master_csv()
        #tracker.driver.set_collect(0) # make sure to turn off collection if we exit early
        #tracker.driver.disconnect()
        