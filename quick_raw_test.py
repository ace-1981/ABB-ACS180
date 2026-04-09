"""Quick raw Modbus test - after wire swap"""
import serial, time

ser = serial.Serial('COM4', 19200, parity='E', stopbits=1, bytesize=8, timeout=1)
ser.reset_input_buffer()

frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
print("Sending:", frame.hex(' '))

for attempt in range(3):
    ser.reset_input_buffer()
    ser.write(frame)
    time.sleep(0.5)
    w = ser.in_waiting
    print(f"Attempt {attempt+1}: {w} bytes waiting")
    if w > 0:
        resp = ser.read(w)
        print(f"  RESPONSE: {resp.hex(' ')}")
        print("  >>> DRIVE IS RESPONDING! <<<")
        break
    time.sleep(0.2)

ser.close()
