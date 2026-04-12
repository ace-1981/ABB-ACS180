"""Find the parameter that controls speed reference source in ACS180."""
from pymodbus.client import ModbusSerialClient
import config, time

client = ModbusSerialClient(
    port=config.COM_PORT, baudrate=config.BAUD_RATE,
    parity=config.PARITY, stopbits=config.STOP_BITS,
    bytesize=config.BYTE_SIZE, timeout=2.0,
)
if not client.connect():
    print("ERROR: Cannot open COM4!")
    exit(1)

print("=== ACS180 Full Parameter Scan ===")
print("Looking for all non-zero parameters...\n")

# Scan all parameter groups that might exist in ACS180
# ACS180 groups: 1-6, 10-13, 19-26, 28-29, 30-37, 50-53, 58, 95-99
groups = list(range(1, 7)) + list(range(10, 14)) + list(range(19, 27)) + \
         [28, 29] + list(range(30, 38)) + list(range(50, 54)) + [58] + \
         list(range(95, 100))

for group in groups:
    found = []
    for param in range(1, 50):
        addr = group * 100 + param
        try:
            res = client.read_holding_registers(address=addr, count=1, device_id=1)
            if hasattr(res, 'registers'):
                val = res.registers[0]
                if val != 0:
                    signed = val if val < 32768 else val - 65536
                    found.append((param, val, signed))
        except:
            pass
    
    if found:
        print(f"--- Group P{group:02d} ---")
        for p, val, signed in found:
            print(f"  P{group:02d}.{p:02d} = {val:6d} (0x{val:04X})  signed={signed}")
        print()

client.close()
print("Done.")
