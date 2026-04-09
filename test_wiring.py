"""
RS485 Wiring Test - ABB ACS180
================================
This script tests the connection repeatedly so you can swap A/B wires
while it's running and see immediately when communication starts.
"""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import time
import sys

PORT = "COM4"
BAUD = 9600
PARITY = "E"
SLAVE_ID = 1

print("=" * 60)
print("  RS485 WIRING TEST - ABB ACS180")
print("=" * 60)
print()
print("  Port:     COM4")
print("  Baud:     9600")
print("  Parity:   Even")
print("  Slave ID: 1")
print()
print("  >>> SWAP A and B wires while this runs <<<")
print("  >>> Press Ctrl+C to stop <<<")
print()
print("-" * 60)

client = ModbusSerialClient(
    port=PORT, baudrate=BAUD, parity=PARITY,
    stopbits=1, bytesize=8, timeout=1.0, retries=1
)

if not client.connect():
    print("  [ERROR] Cannot open COM4!")
    sys.exit(1)

print("  COM4 open. Testing every 2 seconds...")
print()

attempt = 0
try:
    while True:
        attempt += 1
        timestamp = time.strftime("%H:%M:%S")

        try:
            result = client.read_holding_registers(address=0, count=3, device_id=SLAVE_ID)
            if hasattr(result, 'registers'):
                print(f"  [{timestamp}] #{attempt} >>> CONNECTED! <<<")
                print(f"  Registers 0-2: {[f'0x{r:04X}' for r in result.registers]}")
                print()
                print("  ==========================================")
                print("  =        CONNECTION SUCCESSFUL!          =")
                print("  ==========================================")
                print()
                print("  Wiring is CORRECT. Keep it this way.")
                print("  You can stop this test (Ctrl+C).")
                print()

                # Keep reading to confirm stable
                for i in range(5):
                    time.sleep(1)
                    r2 = client.read_holding_registers(address=0, count=5, device_id=SLAVE_ID)
                    if hasattr(r2, 'registers'):
                        print(f"  [{time.strftime('%H:%M:%S')}] Stable read: {[f'0x{r:04X}' for r in r2.registers]}")
                    else:
                        print(f"  [{time.strftime('%H:%M:%S')}] Lost connection!")

                break
            else:
                print(f"  [{timestamp}] #{attempt} No response (try swapping A/B)")
        except (ModbusIOException, Exception) as e:
            print(f"  [{timestamp}] #{attempt} No response (try swapping A/B)")

        time.sleep(2)

except KeyboardInterrupt:
    print("\n  Stopped.")
finally:
    client.close()
    print("  Port closed.")
