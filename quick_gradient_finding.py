import numpy as np
import os
import pandas as pd
from pathlib import Path



raw_path = Path(
    input(f"Enter or drag & drop the folder path: ").strip().strip('"')
)

folder_path = Path(raw_path).resolve()


# List all Excel files in the folder
csv_files = list(folder_path.glob("*.[cC][sS][vV]"))

if not csv_files:
    print("No CSV files found in the specified folder.")
else:
    for file in csv_files:
        file_path = Path(folder_path) / file # find the file path 
        df = pd.read_csv(file_path) #read that into a dataframe 
        x = df["Time (s)"].values
        y = df["Droplet Count"].values
        x = x[:,np.newaxis] # make it the right shape for lstsq

        a, _, _, _ = np.linalg.lstsq(x,y)
        print(f"Gradient for {file.name}: {a[0]:.4f} droplets/s")


