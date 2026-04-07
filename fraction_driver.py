import socket
import time

class AzuraFC61:
    def __init__(self, ip="169.254.56.105", port=10001, timeout=5):
        """
        Initializes the driver for Ethernet communication.
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        """Establishes a TCP/IP connection to the device."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.ip, self.port))
        print(f"Connected to Azura FC61 at {self.ip}:{self.port}")

    def disconnect(self):
        """Closes the connection."""
        self.set_local()  # Ensure we return to LOCAL mode before disconnecting
        if self.sock:
            self.sock.close()
            print(f"Disconnected from Azura FC61 at {self.ip}:{self.port}")

    def _send_command(self, command):
        if not self.sock:
            raise ConnectionError("No socket object found. Call connect() first.")
    
        try:
            full_command = f"{command}\r".encode('ascii')
            self.sock.sendall(full_command)
            return self.sock.recv(4096).decode('ascii').strip()
        except OSError as e:
            # This catches [WinError 10038] and other socket-level deaths
            self.sock = None # Clear the broken socket
            raise ConnectionError(f"Communication link lost: {e}")
    

    def identify(self):
        """Returns general device information[cite: 448]."""
        return self._send_command("IDENTIFY?")

    def set_remote(self, timeout_ms=0, priority=1):
        """
        Sets the instrument to REMOTE mode to lock GUI input[cite: 452].
        priority 1 = full read/write access[cite: 454].
        """
        return self._send_command(f"REMOTE:{timeout_ms},1,,{priority}")

    def set_local(self):
        """Unlocks GUI keyboard and returns to LOCAL mode[cite: 456]."""
        return self._send_command("LOCAL")

    def get_status(self):
        """Returns the full status string of the device[cite: 57]."""
        return self._send_command("STATUS?")

    def move_to_vial(self, vial_name, collect_mode=0):
        """
        Moves the needle to a specific vial name (e.g., 'A1')[cite: 126].
        collect_mode 1 = Start collecting after move[cite: 134].
        """
        return self._send_command(f"MOVE:{vial_name},{collect_mode}")

    def move_next(self, collect_mode=2):
        """Moves to the next position in the sequence[cite: 133]."""
        return self._send_command(f"NEXT:{collect_mode}")

    def rehome(self, mode=0):
        """Reinitializes drives and moves to home position[cite: 487]."""
        return self._send_command(f"REHOME:{mode}")

    def set_collect(self, state):
        """Switches the collecting valve: 1 for COLLECT, 0 for WASTE[cite: 486]."""
        return self._send_command(f"COLLECT:{state}")
    
    def sample(self, duration):
        """
        Collects a sample for a specified duration (in seconds).
        If position is provided, moves to that position before collecting.
        """
        self.move_next(collect_mode=0)  # Move to the next position without collecting
        time.sleep(1)  # Wait for the move to complete
        self.set_collect(1)  # Start collecting
        print(f"Starting sample collection for {duration} seconds.")
        time.sleep(duration)  # Collect for the specified duration
        self.set_collect(0)  # Stop collecting
        print("Sample collection complete.")