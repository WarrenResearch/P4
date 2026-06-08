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
import pumpWidget as pw
import platformControl as pc

''''
designed for one pump at a time, do not use more than 1 - to test multiple pumps, run this script when connected to each pump separately. 

uses fraction_driver, if calibration is needed using a different method add it here

You will need to check self.reactor_volume is the correct volume for your calibration
'''

class DropletCounter:
    def __init__(self,widget,driver=None):
        # Reuse the already-connected fraction collector when available.
        self.driver = driver if driver is not None else fraction_driver.AzuraFC61()

        if getattr(self.driver, "sock", None) is None:
            self.driver.connect()

        # Keep the collector in remote mode before sending motion/collect commands.
        self.driver.set_remote()
        time.sleep(2) # Give it a moment to switch modes
        self.driver.set_collect(1) 
        
        self.widget = widget # holds live reference to widget (so your calibration value goes to the correct place)
        self.reactor_volume_ml = 0.1 # change this with your volume, in my case im not using the whole reacotr for the calibration 

        # --- Experiment Settings ---
        self.flowrate_list = [0.1, 0.25, 0.5] 
        self.runs_per_flowrate = 3 
        self.maximum_duration_min = 5 
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
        
        print(f"\n setting flowrates and waiting for steady state...")
        self.widget.setFlowrateText.setText(str(current_flowrate))
        self.widget.setFlowrate()
        self.widget.start()
        
        if self.current_run_idx == 0:
            steady_state_minutes = 3 * (self.reactor_volume_ml / current_flowrate)
            steady_state_seconds = steady_state_minutes * 60

            QTimer.singleShot(int(steady_state_seconds*1000),self.activate_measurement_timer)
        else:
            self.activate_measurement_timer()
    
    def activate_measurement_timer(self):
        self.start_time = time.time() 
        self.droplet_count = [] 
        self.timestamps = [] 
        self.baseline_count = int(self.driver.drop_count())
        self.timer.start(5000) # Poll every 5 seconds

    def get_droplet_count(self):
        drop_count = int(self.driver.drop_count())
        relative_count = drop_count - self.baseline_count
        #if not hasattr(self, '_fake_hardware_count'):
        #    self._fake_hardware_count = 0
        #self._fake_hardware_count += random.randint(0, 5) 
        try:
            return int(relative_count)
        except (TypeError, ValueError):
            return 0
    
    def poll_droplet_count(self):
        current_time = time.time()
        duration = current_time - self.start_time 

        current_flowrate = self.flowrate_list[self.current_flow_idx]
        run_number = self.current_run_idx + 1

        # grab data point first so the final interval isn't missed due to timer stop
        relative_count = self.get_droplet_count()
        self.droplet_count.append(int(relative_count))   
        self.timestamps.append(duration)

        print(f"[{current_flowrate} mL/min | Run {run_number}] Time: {duration:.0f}s, Droplets: {relative_count}")

        #  Check if this specific run window is completed
        if duration >= self.maximum_duration_s:
            self.timer.stop() 

            # Calculate average for this specific run window
            droplet_average = self.droplet_count[-1]/self.maximum_duration_min if self.droplet_count else 0
            self.summary_averages[current_flowrate].append(droplet_average)

            print(f"-> Finished Run {run_number} (@ {current_flowrate} mL/min). Average Droplets per min: {droplet_average:.2f}")

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
                    self.driver.set_collect(0)
                    self.calibration_gradient()
                    self.disconnect_hardware()
                    print(f"\nAll experiments complete! Master CSV saving...")
                    self.save_master_csv()
                    calibration_factor = self.calibration_factor()

                    self.widget.calibrationFactorText.setText(f"{calibration_factor:.4f}")
                    print("Pump Claibrated with factor: ", calibration_factor)





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
    
    def calibration_factor(self):
        expected_gradient = 59.127 # calibration of pump fr vs droplet count
        correction_factor = expected_gradient / self.master_records[0]['Calibration Gradient']
        return correction_factor
    
    def disconnect_hardware(self):
        print("Disconnecting hardware...")
        self.driver.disconnect() 
        self.widget.stop()