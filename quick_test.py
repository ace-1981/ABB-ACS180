"""Quick connection test after 58.06 refresh"""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

print("Testing COM4 - Slave=1, Baud=9600, Parity=Even...")
client = ModbusSerialClient(port="COM4", baudrate=9600, parity="E", stopbits=1, bytesize=8, timeout=2, retries=2)
if not client.connect():
    print("ERROR: Cannot open COM4")
    exit()
print("Port open.")

try:
    result = client.read_holding_registers(address=0, count=5, device_id=1)
    if hasattr(result, "registers"):
        print()
        print("=" * 40)
        print("   >>> CONNECTED! <<<")
        print("=" * 40)
        for i, r in enumerate(result.registers):
            print(f"  Register {i}: {r} (0x{r:04X})")
    else:
        print("No response from drive.")
except ModbusIOException as e:
    print(f"No response: {e}")
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
    print("Port closed.")
