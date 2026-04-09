"""Final converter test - replug USB then run this"""
import serial
import serial.tools.list_ports
import time

print("=" * 50)
print("  CHECKING ALL COM PORTS")
print("=" * 50)

ports = list(serial.tools.list_ports.comports())
if not ports:
    print("  No COM ports found!")
    exit()

for p in ports:
    print(f"\n  Testing {p.device} ({p.description})...")
    try:
        ser = serial.Serial(p.device, 9600, parity="N", timeout=1)
        test_data = bytes([0xAA, 0x55, 0xAA, 0x55])
        
        # Try with different RTS states
        for rts_val in [True, False]:
            ser.rts = rts_val
            time.sleep(0.05)
            ser.reset_input_buffer()
            ser.write(test_data)
            time.sleep(0.3)
            rx = ser.in_waiting
            if rx > 0:
                data = ser.read(rx)
                print(f"    RTS={rts_val}: GOT {rx} bytes: {data.hex(' ')}")
                print(f"    >>> WORKING! <<<")
            else:
                print(f"    RTS={rts_val}: no echo")
        ser.close()
    except Exception as e:
        print(f"    Error: {e}")

print("\n" + "=" * 50)
