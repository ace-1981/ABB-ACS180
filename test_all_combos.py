"""Try all baud/parity combinations from the ACS180 manual"""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import serial
import time

PORT = "COM4"

# From manual: 58.04 baud: [1]4800 [2]9600 [3]19200 [4]38400 [5]57600 [6]76800 [7]115200
# From manual: 58.05 parity: [0]8N1 [1]8N2 [2]8E1 [3]8O1
combos = [
    (9600,  "E", 1, "58.04=2, 58.05=2 (9600 8E1)"),
    (9600,  "N", 1, "58.04=2, 58.05=0 (9600 8N1) - DEFAULT?"),
    (9600,  "N", 2, "58.04=2, 58.05=1 (9600 8N2)"),
    (9600,  "O", 1, "58.04=2, 58.05=3 (9600 8O1)"),
    (19200, "E", 1, "58.04=3, 58.05=2 (19200 8E1)"),
    (19200, "N", 1, "58.04=3, 58.05=0 (19200 8N1)"),
    (4800,  "E", 1, "58.04=1, 58.05=2 (4800 8E1)"),
    (4800,  "N", 1, "58.04=1, 58.05=0 (4800 8N1)"),
]

print("=" * 60)
print("  ACS180 - Testing ALL manual baud/parity combos on COM4")
print("=" * 60)

for baud, par, stop, desc in combos:
    client = ModbusSerialClient(port=PORT, baudrate=baud, parity=par, stopbits=stop, bytesize=8, timeout=1, retries=1)
    if not client.connect():
        print(f"  SKIP {desc} - port busy")
        continue
    try:
        r = client.read_holding_registers(address=0, count=1, device_id=1)
        if hasattr(r, "registers"):
            print(f"  >>> FOUND: {desc} = {r.registers[0]} (0x{r.registers[0]:04X})")
            # Read more
            r2 = client.read_holding_registers(address=0, count=10, device_id=1)
            if hasattr(r2, "registers"):
                print(f"      Regs 0-9: {[f'0x{v:04X}' for v in r2.registers]}")
            client.close()
            break
        else:
            print(f"  No response: {desc}")
    except (ModbusIOException, Exception):
        print(f"  No response: {desc}")
    client.close()
else:
    print()
    print("  Still no response on ANY combination.")
    print()
    # Raw loopback test
    print("  LOOPBACK TEST (checking if converter sends):")
    try:
        ser = serial.Serial(PORT, 9600, parity="N", stopbits=1, bytesize=8, timeout=1)
        # Modbus frame: slave=1, FC=03, addr=0, count=1
        frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
        ser.write(frame)
        time.sleep(0.5)
        rx = ser.in_waiting
        if rx > 0:
            data = ser.read(rx)
            print(f"  Got {rx} bytes back: {data.hex(' ')}")
            if data == frame:
                print("  >>> THIS IS ECHO! RS485 wires might be shorted")
                print("  >>> or converter TX is looping back to RX")
        else:
            print(f"  0 bytes received (not even echo)")
            print()
            print("  POSSIBLE ISSUES:")
            print("  1. Converter not sending - check TX LED")
            print("  2. Wrong terminals on drive")
            print("  3. Cable broken or too long")
            print("  4. Need termination resistor")
        ser.close()
    except Exception as e:
        print(f"  Loopback error: {e}")

print("=" * 60)
