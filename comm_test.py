"""
ABB ACS180 – Communication Diagnostic
=======================================
Focused test: is the drive responding at ALL?
Tests raw serial + Modbus at multiple settings.
"""
import serial
import time
import sys

PORT = "COM4"

print("=" * 60)
print("  ACS180 COMMUNICATION DIAGNOSTIC")
print("  Port: " + PORT)
print("=" * 60)

# ─────────────────────────────────────────────
# Step 1: Can we open the port?
# ─────────────────────────────────────────────
print("\n[1/4] OPENING SERIAL PORT...")
try:
    ser = serial.Serial(PORT, 19200, parity='E', stopbits=1, bytesize=8, timeout=1)
    print(f"  OK - Port is open: {ser.name}")
    print(f"  Settings: {ser.baudrate} baud, {ser.bytesize}{ser.parity}{ser.stopbits}")
    ser.close()
except Exception as e:
    print(f"  FAILED: {e}")
    print("  >>> Check: Is USB-RS485 adapter plugged in?")
    print("  >>> Check: Is COM4 the right port? (Device Manager)")
    sys.exit(1)

# ─────────────────────────────────────────────
# Step 2: Raw Modbus frames at ALL baud rates
# ─────────────────────────────────────────────
print("\n[2/4] RAW MODBUS TEST (slave=1, read reg 0)")
print("-" * 50)

# Modbus RTU frame: Slave=01, FC=03 (read holding), Addr=0x0000, Count=0x0001
# CRC is independent of baud/parity - calculated on data bytes
frame_data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01])

def calc_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

raw_frame = frame_data + calc_crc(frame_data)
print(f"  Frame to send: {raw_frame.hex(' ')}")

configs = [
    (19200, 'E', 1, "19200/8E1 - Your drive setting (P58.04/P58.05)"),
    (9600,  'E', 1, "9600/8E1  - ABB default"),
    (19200, 'N', 2, "19200/8N2 - Alternative"),
    (9600,  'N', 2, "9600/8N2  - Alternative"),
    (19200, 'N', 1, "19200/8N1 - Alternative"),
    (9600,  'N', 1, "9600/8N1  - Alternative"),
    (38400, 'E', 1, "38400/8E1 - Higher speed"),
]

found_config = None

for baud, par, stop, desc in configs:
    try:
        ser = serial.Serial(PORT, baud, parity=par, stopbits=stop, bytesize=8, timeout=0.5)
        # Flush any stale data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.05)
        
        ser.write(raw_frame)
        time.sleep(0.3)
        
        waiting = ser.in_waiting
        if waiting > 0:
            resp = ser.read(waiting)
            print(f"  >>> RESPONSE at {desc}")
            print(f"      Bytes: {resp.hex(' ')}")
            print(f"      Length: {waiting} bytes")
            found_config = (baud, par, stop)
            ser.close()
            break
        else:
            print(f"  No response: {desc}")
        ser.close()
    except Exception as e:
        print(f"  Error at {desc}: {e}")

# ─────────────────────────────────────────────
# Step 3: PyModbus library test
# ─────────────────────────────────────────────
print("\n[3/4] PYMODBUS LIBRARY TEST")
print("-" * 50)

from pymodbus.client import ModbusSerialClient

if found_config:
    baud, par, stop = found_config
    print(f"  Using working config: {baud}/{par}/{stop}")
else:
    # Try both main candidates
    baud, par, stop = 19200, 'E', 1
    print(f"  No raw response found. Trying {baud}/8{par}{stop} via pymodbus...")

for test_baud, test_par in [(19200, 'E'), (9600, 'E')]:
    client = ModbusSerialClient(
        port=PORT, baudrate=test_baud, parity=test_par,
        stopbits=1, bytesize=8, timeout=2, retries=3
    )
    
    if not client.connect():
        print(f"  Cannot open port at {test_baud}/{test_par}")
        continue
    
    print(f"\n  Testing {test_baud}/8{test_par}1 via pymodbus:")
    
    # Test read holding registers (FC03)
    for reg in [0, 1, 2, 3, 4, 5]:
        try:
            result = client.read_holding_registers(address=reg, count=1, device_id=1)
            if hasattr(result, 'registers'):
                print(f"    Holding Reg {reg}: {result.registers[0]} (0x{result.registers[0]:04X}) <<<< WORKING!")
            else:
                print(f"    Holding Reg {reg}: Error - {result}")
        except Exception as e:
            print(f"    Holding Reg {reg}: Exception - {e}")
    
    # Test input registers (FC04) 
    for reg in [0, 1, 2, 3, 4, 5]:
        try:
            result = client.read_input_registers(address=reg, count=1, device_id=1)
            if hasattr(result, 'registers'):
                print(f"    Input Reg {reg}:   {result.registers[0]} (0x{result.registers[0]:04X}) <<<< WORKING!")
            else:
                print(f"    Input Reg {reg}:   Error - {result}")
        except Exception as e:
            print(f"    Input Reg {reg}:   Exception - {e}")
    
    client.close()

# ─────────────────────────────────────────────
# Step 4: Scan slave addresses 1-5
# ─────────────────────────────────────────────
print("\n[4/4] SLAVE ADDRESS SCAN (1-5)")
print("-" * 50)

for test_baud in [19200, 9600]:
    client = ModbusSerialClient(
        port=PORT, baudrate=test_baud, parity='E',
        stopbits=1, bytesize=8, timeout=0.5
    )
    if not client.connect():
        continue
    
    for slave in range(1, 6):
        try:
            result = client.read_holding_registers(address=0, count=1, device_id=slave)
            if hasattr(result, 'registers'):
                print(f"  Slave {slave} at {test_baud} baud: RESPONDS! Reg0={result.registers[0]:04X}")
        except:
            pass
    client.close()

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
if found_config:
    b, p, s = found_config
    print(f"  RESULT: Drive RESPONDS at {b} baud, 8{p}{s}")
    print(f"  Update config.py: BAUD_RATE = {b}, PARITY = '{p}'")
else:
    print("  RESULT: NO RESPONSE from drive on any setting.")
    print()
    print("  Check these things:")
    print("  1. WIRING: A+ to A+, B- to B-  (or try swapping A/B)")
    print("  2. DRIVE PANEL: P58.01 = Modbus RTU (is it saved?)")
    print("  3. P58.06: Did you do 'Refresh settings'?")
    print("  4. TERMINATION: 120 ohm resistor on last device?")
    print("  5. USB-RS485 adapter: TX/RX LEDs - does TX blink?")
    print("  6. POWER: Is the drive powered on and not in fault?")
    print("     Fault 6681 = comm loss. Reset it on the panel,")
    print("     then run this test again QUICKLY.")
    print("  7. Try swapping the A and B wires on the RS485")
print("=" * 60)
