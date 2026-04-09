"""Check FTDI converter RS485 settings and try fixing"""
import serial
import serial.tools.list_ports
import time

PORT = "COM4"

print("=" * 50)
print("  FTDI CONVERTER DIAGNOSTIC")
print("=" * 50)

# List all ports with details
print("\n  All COM ports:")
for p in serial.tools.list_ports.comports():
    print(f"  {p.device}: {p.description}")
    print(f"    VID:PID = {p.vid}:{p.pid}")
    print(f"    Serial#: {p.serial_number}")
    print(f"    Product: {p.product}")
    print(f"    HWID: {p.hwid}")

# Test with RTS/DTR control (some FTDI use these for TX enable)
print("\n  Testing with RTS/DTR control...")
configs = [
    {"rts": True,  "dtr": True,  "desc": "RTS=HIGH, DTR=HIGH"},
    {"rts": False, "dtr": False, "desc": "RTS=LOW,  DTR=LOW"},
    {"rts": True,  "dtr": False, "desc": "RTS=HIGH, DTR=LOW"},
    {"rts": False, "dtr": True,  "desc": "RTS=LOW,  DTR=HIGH"},
]

test_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0xAA, 0xBB, 0xCC])

for cfg in configs:
    try:
        ser = serial.Serial(PORT, 9600, parity="N", stopbits=1, bytesize=8, timeout=1)
        ser.rts = cfg["rts"]
        ser.dtr = cfg["dtr"]
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.write(test_data)
        time.sleep(0.3)
        rx = ser.in_waiting
        if rx > 0:
            data = ser.read(rx)
            print(f"  {cfg['desc']} -> GOT {rx} bytes: {data.hex(' ')}")
            if data == test_data:
                print(f"  >>> ECHO WORKS with {cfg['desc']}! <<<")
        else:
            print(f"  {cfg['desc']} -> no echo")
        ser.close()
    except Exception as e:
        print(f"  {cfg['desc']} -> error: {e}")

# Test with rs485_mode if available
print("\n  Testing RS485 mode flag...")
try:
    ser = serial.Serial(PORT, 9600, parity="N", stopbits=1, bytesize=8, timeout=1)
    if hasattr(ser, 'rs485_mode'):
        try:
            ser.rs485_mode = serial.rs485.RS485Settings(
                rts_level_for_tx=True,
                rts_level_for_rx=False,
                delay_before_tx=0.0,
                delay_before_rx=0.0
            )
            ser.reset_input_buffer()
            ser.write(test_data)
            time.sleep(0.3)
            rx = ser.in_waiting
            if rx > 0:
                data = ser.read(rx)
                print(f"  RS485 mode (rts_tx=True) -> GOT {rx} bytes: {data.hex(' ')}")
            else:
                print(f"  RS485 mode (rts_tx=True) -> no echo")
        except Exception as e:
            print(f"  RS485 mode error: {e}")
            print(f"  (This is normal on Windows - RS485 mode is Linux only)")
    else:
        print("  rs485_mode not available on this platform")
    ser.close()
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 50)
