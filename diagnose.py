"""
RS485 Deep Diagnostic - ABB ACS180
====================================
Tests EVERYTHING: raw bytes, multiple function codes,
different parity modes, input vs holding registers.
"""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import serial
import time
import sys

PORT = "COM4"

print("=" * 60)
print("  RS485 DEEP DIAGNOSTIC - COM4")
print("=" * 60)

# ── Step 1: Raw serial port test ──────────────────────
print("\n[1/5] RAW SERIAL PORT TEST")
print("-" * 40)
try:
    ser = serial.Serial(PORT, 9600, parity='E', stopbits=1, bytesize=8, timeout=1)
    print(f"  Port open: {ser.is_open}")
    print(f"  Port settings: {ser.baudrate} {ser.bytesize}{ser.parity}{ser.stopbits}")

    # Send a raw Modbus request: Read Holding Register 0 from Slave 1
    # Frame: [Slave=01] [Func=03] [Addr=0000] [Count=0001] [CRC]
    raw_request = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
    print(f"  Sending raw Modbus frame: {raw_request.hex(' ')}")
    ser.write(raw_request)
    time.sleep(0.5)

    waiting = ser.in_waiting
    print(f"  Bytes waiting in buffer: {waiting}")
    if waiting > 0:
        response = ser.read(waiting)
        print(f"  >>> RAW RESPONSE: {response.hex(' ')}")
        print(f"  >>> SOMETHING IS RESPONDING!")
    else:
        print(f"  No response bytes received.")

        # Try slave 0 (broadcast - some devices respond)
        raw_broadcast = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x01, 0x85, 0xDB])
        print(f"\n  Trying broadcast (slave 0): {raw_broadcast.hex(' ')}")
        ser.write(raw_broadcast)
        time.sleep(0.5)
        waiting = ser.in_waiting
        print(f"  Bytes waiting: {waiting}")
        if waiting > 0:
            response = ser.read(waiting)
            print(f"  >>> RAW RESPONSE: {response.hex(' ')}")

    ser.close()
except Exception as e:
    print(f"  Error: {e}")

# ── Step 2: Loopback test ────────────────────────────
print("\n[2/5] LOOPBACK TEST (is converter sending?)")
print("-" * 40)
print("  If converter TX/RX LEDs blink, it's sending data.")
try:
    ser = serial.Serial(PORT, 9600, parity='E', stopbits=1, bytesize=8, timeout=1)
    test_data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
    ser.write(test_data)
    time.sleep(0.1)
    print(f"  Sent {len(test_data)} bytes. Check if converter TX LED blinked.")
    ser.close()
except Exception as e:
    print(f"  Error: {e}")

# ── Step 3: Try all parity + stop bit combos ─────────
print("\n[3/5] TRYING ALL PARITY + STOP BIT COMBOS")
print("-" * 40)
combos = [
    (9600, 'E', 1),  # Standard ABB
    (9600, 'N', 2),  # Some devices use N,8,2
    (9600, 'N', 1),  # Common alternative
    (9600, 'O', 1),  # Odd parity
    (19200, 'E', 1), # Higher baud
    (19200, 'N', 2),
]

for baud, par, stop in combos:
    try:
        ser = serial.Serial(PORT, baud, parity=par, stopbits=stop, bytesize=8, timeout=0.5)
        # Modbus read holding reg 0, slave 1
        raw = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A])
        ser.write(raw)
        time.sleep(0.3)
        waiting = ser.in_waiting
        if waiting > 0:
            resp = ser.read(waiting)
            print(f"  >>> RESPONSE at Baud={baud} Parity={par} Stop={stop}: {resp.hex(' ')}")
        else:
            print(f"  No response: Baud={baud} Parity={par} Stop={stop}")
        ser.close()
    except Exception as e:
        print(f"  Error at {baud}/{par}/{stop}: {e}")

# ── Step 4: Try different Modbus functions ────────────
print("\n[4/5] TRYING DIFFERENT MODBUS FUNCTIONS")
print("-" * 40)
try:
    client = ModbusSerialClient(port=PORT, baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=1, retries=1)
    client.connect()

    tests = [
        ("Read Holding Regs (FC03) addr=0", lambda: client.read_holding_registers(address=0, count=1, device_id=1)),
        ("Read Input Regs (FC04) addr=0", lambda: client.read_input_registers(address=0, count=1, device_id=1)),
        ("Read Coils (FC01) addr=0", lambda: client.read_coils(address=0, count=1, device_id=1)),
        ("Read Holding Regs addr=1", lambda: client.read_holding_registers(address=1, count=1, device_id=1)),
        ("Read Holding Regs addr=100", lambda: client.read_holding_registers(address=100, count=1, device_id=1)),
        ("Read Holding Regs addr=400", lambda: client.read_holding_registers(address=400, count=1, device_id=1)),
        ("Read Holding Regs addr=1000", lambda: client.read_holding_registers(address=1000, count=1, device_id=1)),
    ]

    for name, func in tests:
        try:
            result = func()
            if hasattr(result, 'registers'):
                print(f"  >>> OK: {name} = {result.registers}")
            elif hasattr(result, 'bits'):
                print(f"  >>> OK: {name} = {result.bits[:8]}")
            else:
                print(f"  No response: {name}")
        except (ModbusIOException, Exception):
            print(f"  No response: {name}")

    client.close()
except Exception as e:
    print(f"  Error: {e}")

# ── Step 5: Check converter hardware ─────────────────
print("\n[5/5] CONVERTER HARDWARE CHECK")
print("-" * 40)
try:
    ser = serial.Serial(PORT, 9600, timeout=1)
    print(f"  Port name: {ser.name}")
    print(f"  DSR: {ser.dsr}")
    print(f"  CTS: {ser.cts}")
    print(f"  RI:  {ser.ri}")
    print(f"  CD:  {ser.cd}")
    ser.close()
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print("""
  If NO response on any test:
  
  1. CHECK CONVERTER:
     - Does it have TX/RX LEDs? Do they blink?
     - Some cheap converters need a driver update
     - Try: short A and B together, send data,
       you should see echo back (loopback test)

  2. CHECK DRIVE TERMINALS:
     - ACS180 has EIA-485 on the I/O board
     - Terminals are usually labeled:
       A+ (or D+), B- (or D-), SG (signal ground)
     - Make sure you're on the RIGHT terminals
       (not analog I/O!)

  3. CHECK DRIVE SETTINGS:
     - On the drive panel, go to Group 58
     - Confirm 58.01 = 1 (Modbus RTU)
     - Some drives need POWER CYCLE after
       changing communication settings!

  4. POWER CYCLE THE DRIVE:
     - Turn off, wait 10 seconds, turn on
     - Some drives only apply Modbus settings
       after a restart!
""")
