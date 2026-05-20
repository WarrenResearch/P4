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
        
        self.timer = QTimer() 
        self.timer.timeout.connect(self.poll_droplet_count) 
        self.start_time = time.time() 

        self.start_count = 0 #int(self.driver.drop_count()) # Get the initial droplet count from the device
        print(f"Starting droplet count: {self.start_count}")

        self.maximum_duration_min = 0.5 # change this for duration of experiment in mins
        self.maximum_duration_s = self.maximum_duration_min * 60

        # data storage area 
        self.droplet_counts = [] 
        self.timestamps = [] 
        self.gradient = []

        self.prev_count = 0
        self.prev_time = self.start_time

        
    def get_droplet_count(self):
        import random

        if not hasattr(self, '_fake_hardware_count'):
            self._fake_hardware_count = 0
        
        self._fake_hardware_count += random.randint(0, 5) # simulate 0-5 droplets every poll
        return self._fake_hardware_count #int(self.driver.drop_count()) 
    
    def total_gradient(self):
        if len(self.timestamps) < 2:
            return 0 
        total_time = self.timestamps[-1] - self.timestamps[0]
        total_count = self.droplet_counts[-1] - self.droplet_counts[0]
        return total_count / total_time if total_time > 0 else 0
    
    def results_to_csv(self, filename=None):
        if filename is None:
            filename = time.strftime("droplet_data_%Y%m%d_%H%M%S.csv", time.localtime(self.start_time))
        results_dir = "calibration_results"
        os.makedirs(results_dir, exist_ok=True)
        filepath = os.path.join(results_dir, filename)

        df = pd.DataFrame({
            "Time (s)": self.timestamps,
            "Droplet Count": self.droplet_counts,
            "Gradient (droplets/s)": self.gradient,
            "total Gradient (droplets/s)": [self.total_gradient()] * len(self.timestamps)
        })
        df.to_csv(filepath, index=False, float_format="%.3f")
        print(f"Results saved to {filepath}")
        
    def poll_droplet_count(self):

        current_time = time.time()

        duration = current_time - self.start_time 

        if duration >= self.maximum_duration_s:
            QApplication.quit()
            print(f"Total Gradient: {self.total_gradient():.2f} droplets/s")
            self.results_to_csv()
            self.results_gradient()
            #self.driver.set_collect(0) # make sure to turn off collection at the end of the experiment
            #self.driver.disconnect()
            return
        
        relative_count = self.get_droplet_count() - self.start_count

        delta_count = relative_count - self.prev_count
        delta_time = current_time - self.prev_time

        gradient = delta_count / delta_time if delta_time > 0 else 0 # avoids div by zero

        self.droplet_counts.append(relative_count)
        self.timestamps.append(duration)
        self.gradient.append(gradient)

        self.prev_count = relative_count
        self.prev_time = current_time
        
        # Adding a print statement so you can see it working in the console
        print(f"Elapsed: {duration:.1f}s | Droplet Count: {relative_count} | Gradient: {gradient:.2f} droplets/s") 
    
    def results_gradient(self):
        #placeholder: this function will take each dataset and find the gradient for each, given y is forced through 0, this is the calibration for each pump
        x = np.array(self.timestamps + [0]) # gives a 0, 0 point for forcing through 0
        y = np.array(self.droplet_counts + [0])

        x = x[:,np.newaxis]
        a, _, _, _ = np.linalg.lstsq(x,y)
        print(a)
        return a




if __name__ == "__main__":
    app = QApplication(sys.argv)

    tracker = DropletCounter() 
    tracker.timer.start(5000) # Start the timer with an explicit 5s interval here

    try:
        sys.exit(app.exec_()) 
    except KeyboardInterrupt:
        tracker.timer.stop()
        tracker.results_to_csv()
        #tracker.driver.set_collect(0) # make sure to turn off collection if we exit early
        #tracker.driver.disconnect()
        