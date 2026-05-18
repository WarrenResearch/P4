import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import time
import fraction_driver
import matplotlib.pyplot as plt
import pandas as pd

class DropletCounter:
    def __init__(self):
        self.driver = fraction_driver.AzuraFC61()
        self.driver.connect() #initiate connection to the device
        self.driver.set_remote(1) #set the fraction collector to remote 
        
        self.timer = QTimer() 
        self.timer.timeout.connect(self.poll_droplet_count) 
        
        self.start_time = time.time() 

        self.start_count = self.driver.droplet_count() # Get the initial droplet count from the device

        self.maximum_duration_min = 0.2 # change this for duration of experiment in mins
        self.maximum_duration_s = self.maximum_duration_min * 60

        # data storage area 
        self.droplet_counts = [] 
        self.timestamps = [] 
        self.gradient = []

        self.prev_count = 0
        self.prev_time = self.start_time

        
    def get_droplet_count(self):
        # Simulated data increasing over time
        return self.driver.droplet_count() 
    
    def total_gradient(self):
        if len(self.timestamps) < 2:
            return 0 
        total_time = self.timestamps[-1] - self.timestamps[0]
        total_count = self.droplet_counts[-1] - self.droplet_counts[0]
        return total_count / total_time if total_time > 0 else 0
    
    def results_to_csv(self, filename="droplet_counts.csv"):
        df = pd.DataFrame({
            "Time (s)": self.timestamps,
            "Droplet Count": self.droplet_counts,
            "Gradient (droplets/s)": self.gradient
        })
        df.to_csv(filename, index=False, float_format="%.3f")
        print(f"Results saved to {filename}")
        
    def poll_droplet_count(self):

        current_time = time.time()

        duration = current_time - self.start_time 

        if duration > self.maximum_duration_s:
            QApplication.quit()
            print(f"Total Gradient: {self.total_gradient():.2f} droplets/s")
            self.results_to_csv()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    tracker = DropletCounter() 
    tracker.timer.start(500) # Start the timer with an explicit 1000ms interval here

    try:
        sys.exit(app.exec_()) 
    except KeyboardInterrupt:
        tracker.timer.stop()
        tracker.results_to_csv()
        