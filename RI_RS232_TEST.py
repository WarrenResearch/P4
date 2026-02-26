import serial
import time
import sys
import threading

SERIAL_PORT = 'COM4' 
BAUD_RATE = 9600

def read_from_port(ser):
    while True:
        try:
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                # Print exactly what the device sends back in raw format
                print(f"\n[DEVICE SAYS]: {response}")
            time.sleep(0.05)
        except:
            break

def start_interactive():
    try:
        ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
        
        # --- THE MAGIC FIX: Assert Hardware Flow Control ---
        ser.dtr = True
        ser.rts = True
        
        print(f"[*] Connected to {SERIAL_PORT}.")
        print("[*] Flow control asserted (DTR & RTS are ON).")
        print("[*] Type 'EXIT' to quit.")
        print("-" * 50)

        listener_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        listener_thread.start()

        while True:
            cmd = input("\nEnter command: ")
            if cmd.upper() == 'EXIT':
                break
            
            # Sending command with Carriage Return (\r) AND Line Feed (\n)
            # Make sure to type commands in ALL CAPS just in case!
            ser.write((cmd + '\r\n').encode('ascii'))
            time.sleep(0.2) 

    except serial.SerialException as e:
        print(f"[!] Serial error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    start_interactive()