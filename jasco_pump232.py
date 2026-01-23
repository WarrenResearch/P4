import serial
import time


'''Jasco PU-2080 Pump Control Class, import this into your python script to use the class.'''


class JascoPU2080:
    def __init__(self, com_port: int): #handles the physical connection logic
        if not (1 <= com_port <= 255):
            raise ValueError("COM port must be 1–255")

        self.ser = serial.Serial(
            port=f"COM{com_port}",
            baudrate=4800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_TWO,
            timeout=1,
            rtscts=True, #hardware handshake 
        )

        # pause after fopen - gives time for the connection to establish before sending commands
        time.sleep(0.4) # potentially not necessary if a ping is used to check if the port is open - worthwhile looking into

    # ---------- low-level communication ----------
    def _comm(self, mode: str, command: str): # handles the raw talking/listening to the pump
        if mode not in ("read", "write"):
            raise ValueError('mode must be "read" or "write"')

        if len(command.split()) > 4:
            raise ValueError("Command must have ≤ 4 words")

        # Flush buffer
        self.ser.reset_input_buffer()

        # Send command (CR terminated)
        self.ser.write((command + "\r").encode("ascii"))

        if mode == "read":
            response = "%%"

            while "%%" in response:
                line = self.ser.readline()
                if not line:
                    raise RuntimeError(
                        f'No response from JASCO pump to "{command}"'
                    )

                response = line.decode("ascii", errors="ignore").rstrip("\r\n")

            return response

        # write-only → mandatory delay
        time.sleep(0.15)

    # ---------- high-level API ---------- (commands you would actually want to use in a script)
    def start(self):
        self._comm("write", "0 pump set") # start pump

    def stop(self):
        self._comm("write", "1 pump set") # stop pump

    def is_running(self) -> bool: # returns True if the pump is running, False otherwise
        return self.read_flow() > 0 # checks if flow is greater than 0 (i.e. pump is running)

    # ---- flow ----
    def read_flow(self) -> float: # returns the current flow in mL/min
        flow = round(float(self._comm("read", "a_flow load p")), 3)

        # safety limit: flow cannot be >10 mL/min
        if flow > 10:
            flow = 0.0

        return flow

    def set_flow(self, flow_ml_min: float): # sets the flow in mL/min
        if not (0 <= flow_ml_min <= 10):
            raise ValueError("Flow must be 0–10 mL/min")

        self._comm("write", f"{flow_ml_min:.3f} flowrate set")

    # ---- pressure ----
    def read_pressure(self) -> float: # returns the current pressure in bar
        return float(self._comm("read", "a_press1 load p"))

    def read_max_pressure(self) -> float: # returns the maximum pressure setting in bar
        return float(self._comm("read", "a_pmax load p"))

    def set_max_pressure(self, pressure_bar: float): # sets the maximum pressure in bar
        if not (0 <= pressure_bar <= 350):
            raise ValueError("Pressure must be 0–350 bar")

        self._comm("write", f"{round(pressure_bar):.0f} pmax set")

    def read_min_pressure(self) -> float: # returns the minimum pressure setting in bar
        return float(self._comm("read", "a_pmin load p"))

    def set_min_pressure(self, pressure_bar: float): # sets the minimum pressure in bar
        if not (0 <= pressure_bar <= 350):
            raise ValueError("Pressure must be 0–350 bar")

        self._comm("write", f"{round(pressure_bar):.0f} pmin set")

    def read_set_pressure(self) -> float: # returns the set (target) pressure in bar
        return float(self._comm("read", "press load p"))

    def set_set_pressure(self, pressure_bar: float): # sets the set (target) pressure in bar
        if not (0 <= pressure_bar <= 350):
            raise ValueError("Pressure must be 0–350 bar")

        self._comm("write", f"{round(pressure_bar):.0f} press set")

    # ---- flow mode ----
    def read_flow_mode(self) -> int: # returns the current flow mode (0 for flow, 1 for pressure)
        return int(self._comm("read", "cfcp load p"))

    def set_flow_mode(self, mode: int): # sets the flow mode (0 for flow, 1 for pressure)
        if mode not in (0, 1):
            raise ValueError("Mode must be 0 (flow) or 1 (pressure)")

        self._comm("write", f"{mode} cfcp set")

    # ---- cleanup ----
    def close(self): # closes the serial connection
        if self.ser.is_open:
            self.ser.close()
