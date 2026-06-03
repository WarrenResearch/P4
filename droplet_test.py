import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import time
import fraction_driver
import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
import random

class DropletCounter:
    def __init__(self):
        # --- Hardware Initialization (Uncomment for real deployment) ---
        # self.driver = fraction_driver.AzuraFC61()
        # self.driver.connect() 
        # time.sleep(1) 
        # self.driver.set_remote(0) 
        # time.sleep(0.5) 
        # self.driver.move_to_vial('C7') 
        # time.sleep(2) 
        # self.driver.set_collect(1) 
        
        # --- Experiment Settings ---
        self.flowrate_list = [0.1, 0.5] 
        self.runs_per_flowrate = 3 
        self.maximum_duration_min = 0.25 
        self.maximum_duration_s = self.maximum_duration_min * 60 

        # --- State Tracking Indexes ---
        self.current_flow_idx = 0
        self.current_run_idx = 0  

        # --- Storage Structs ---
        # FIX: Track records sequentially as rows to prevent Pandas length mismatch errors
        self.master_records = [] 
        self.summary_averages = {flow: [] for flow in self.flowrate_list}

        # --- Timer Setup ---
        self.timer = QTimer() 
        self.timer.timeout.connect(self.poll_droplet_count) 
        
        self.start_new_run()

    def start_new_run(self):
        current_flowrate = self.flowrate_list[self.current_flow_idx]
        run_number = self.current_run_idx + 1
        
        print(f"\n--- Starting Run {run_number} of {self.runs_per_flowrate} for Flowrate: {current_flowrate} mL/min ---")
        
        # self.driver.set_flowrate(current_flowrate) 

        self.start_time = time.time() 
        self.droplet_count = [] 
        self.timestamps = [] 
        self._fake_hardware_count = 0 

        self.timer.start(5000) # Poll every 5 seconds

    def get_droplet_count(self):
        if not hasattr(self, '_fake_hardware_count'):
            self._fake_hardware_count = 0
        self._fake_hardware_count += random.randint(0, 5) 
        return self._fake_hardware_count 
    
    def poll_droplet_count(self):
        current_time = time.time()
        duration = current_time - self.start_time 

        current_flowrate = self.flowrate_list[self.current_flow_idx]
        run_number = self.current_run_idx + 1

        # 1. Grab data point first so the final interval isn't missed
        relative_count = self.get_droplet_count()
        self.droplet_count.append(relative_count)   
        self.timestamps.append(duration)

        print(f"[{current_flowrate} mL/min | Run {run_number}] Time: {duration:.0f}s, Droplets: {relative_count}")

        # 2. Check if this specific run window is completed
        if duration >= self.maximum_duration_s:
            self.timer.stop() 

            # Calculate average for this specific run window
            droplet_average = np.mean(self.droplet_count) if self.droplet_count else 0
            self.summary_averages[current_flowrate].append(droplet_average)

            print(f"-> Finished Run {run_number} (@ {current_flowrate} mL/min). Average Droplets: {droplet_average:.2f}")

            # Append the completed time-series data for this run into master records
            for ts, count in zip(self.timestamps, self.droplet_count):
                self.master_records.append({
                    "Flowrate (mL/min)": current_flowrate,
                    "Run": run_number,
                    "Time (s)": round(ts),
                    "Droplet Count": count,
                    "Run Average": round(droplet_average, 3)
                })

            # State Logic: Move to next run or next flowrate
            if self.current_run_idx < (self.runs_per_flowrate - 1):
                self.current_run_idx += 1
                self.start_new_run()
            else:
                # Calculate overall average for this completed flowrate block
                overall_avg = np.mean(self.summary_averages[current_flowrate])
                print(f"==> OVERALL AVERAGE FOR {current_flowrate} mL/min: {overall_avg:.2f} droplets <==")
                
                # Apply the final overall average back onto the records of this specific flowrate block
                for record in self.master_records:
                    if record["Flowrate (mL/min)"] == current_flowrate:
                        record["Overall Average"] = round(overall_avg, 3)

                if self.current_flow_idx < (len(self.flowrate_list) - 1):
                    self.current_flow_idx += 1
                    self.current_run_idx = 0
                    self.start_new_run()
                else:
                    self.calibration_gradient()

                    print(f"\nAll experiments complete! Master CSV saving...")
                    self.save_master_csv()
                    QApplication.quit() 

    def save_master_csv(self):
        results_dir = 'calibration_results'
        os.makedirs(results_dir, exist_ok=True)
        timestamp_str = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(results_dir, f'calibration_data_{timestamp_str}.csv')

        # This row-by-row structure safely converts to a Dataframe without length limits!
        df = pd.DataFrame(self.master_records)
        df.to_csv(filepath, index=False, float_format='%.3f')
        print(f'Master CSV safely written to: {filepath}')


    def calibration_gradient(self):
        x_flowrates = []
        y_averages = []

        for flowrate, avgs_list in self.summary_averages.items():
            if avgs_list:
                x_flowrates.append(flowrate)
                y_averages.append(np.mean(avgs_list))
            else:
                print("No averages available to plot.")
                return None
        
        x = np.array(x_flowrates)
        y = np.array(y_averages)

        x = x[:,np.newaxis]
        gradient, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
        for record in self.master_records:
            record['Calibration Gradient'] = round(gradient[0],4)
            
        return gradient[0]
    

    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = DropletCounter()
    try:
        sys.exit(app.exec_()) 
    except KeyboardInterrupt:
        tracker.timer.stop()
        if tracker.master_records:
            tracker.save_master_csv()