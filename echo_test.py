"""Check if the 0x00 byte is echo or real response"""
import serial, time

ser = serial.Serial('COM4', 19200, parity='E', stopbits=1, bytesize=8, timeout=2)
print("=== ECHO vs REAL RESPONSE TEST ===\n")

# Test 1: Send different frames and see if response changes
frames = [
    (bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A]), "Read reg 0, slave 1"),
    (bytes([0x01, 0x03, 0x00, 0x01, 0x00, 0x01, 0xD5, 0xCA]), "Read reg 1, slave 1"),
    (bytes([0x02, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x39]), "Read reg 0, slave 2"),
    (bytes([0x01, 0x06, 0x00, 0x00, 0x00, 0x00, 0x89, 0xCA]), "Write 0 to reg 0, slave 1"),
]

for frame, desc in frames:
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)
    
    ser.write(frame)
    time.sleep(1.0)
    
    w = ser.in_waiting
    if w > 0:
        resp = ser.read(w)
        print(f"{desc}")
        print(f"  TX: {frame.hex(' ')}")
        print(f"  RX: {resp.hex(' ')} ({w} bytes)")
    else:
        print(f"{desc}: No response")
    print()

# Test 2: Don't send anything - see if we still get 0x00
print("--- SILENCE TEST (not sending anything, waiting 2 sec) ---")
ser.reset_input_buffer()
time.sleep(2.0)
w = ser.in_waiting
if w > 0:
    resp = ser.read(w)
    print(f"  Got {w} bytes WITHOUT sending: {resp.hex(' ')}")
    print(f"  >>> This is NOISE on the line, not a real response!")
else:
    print(f"  No bytes received (clean line)")

# Test 3: Try 9600 baud
print("\n--- TRYING 9600 BAUD ---")
ser.close()
ser = serial.Serial('COM4', 9600, parity='E', stopbits=1, bytesize=8, timeout=2)
frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
ser.reset_input_buffer()
ser.write(frame)
time.sleep(1.0)
w = ser.in_waiting
if w > 0:
    resp = ser.read(w)
    print(f"  RX at 9600: {resp.hex(' ')} ({w} bytes)")
else:
    print(f"  No response at 9600")

ser.close()
print("\nDone.")
