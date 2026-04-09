"""Extended raw Modbus test - drive is starting to respond!"""
import serial, time

ser = serial.Serial('COM4', 19200, parity='E', stopbits=1, bytesize=8, timeout=2)
print("Port open: COM4 @ 19200/8E1")

frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])

for attempt in range(5):
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)
    
    print(f"\nAttempt {attempt+1}:")
    print(f"  TX: {frame.hex(' ')}")
    ser.write(frame)
    
    # Wait longer for response
    time.sleep(1.0)
    
    w = ser.in_waiting
    print(f"  Bytes waiting: {w}")
    if w > 0:
        resp = ser.read(w)
        print(f"  RX: {resp.hex(' ')}")
        print(f"  Length: {len(resp)} bytes")
        
        if len(resp) >= 5:
            print(f"  Slave: {resp[0]}")
            print(f"  Function: {resp[1]}")
            if resp[1] == 0x03:
                byte_count = resp[2]
                print(f"  Byte count: {byte_count}")
                if len(resp) >= 5:
                    value = (resp[3] << 8) | resp[4]
                    print(f"  Register value: {value} (0x{value:04X})")
                    print("  >>> FULL VALID RESPONSE! <<<")
            elif resp[1] == 0x83:
                print(f"  EXCEPTION code: {resp[2]}")
                print("  (Drive responded with error - but communication WORKS!)")
        elif len(resp) >= 1:
            print("  Partial response - drive is trying to communicate")
    else:
        print("  No response")
    
    time.sleep(0.5)

ser.close()
print("\nDone.")
