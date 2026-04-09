"""Read and test ACS180 parameter group 19 via Modbus"""
from pymodbus.client import ModbusSerialClient
import time

c = ModbusSerialClient(port='COM4', baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=2)
if not c.connect():
    print("Cannot open COM4")
    exit()

print("=" * 60)
print("  ACS180 - PARAMETER GROUP 19 SCAN")
print("=" * 60)

# ABB ACS180: Parameters are often accessed via register = (group * 100) + index
# So P19.11 might be at register 1911, P19.12 at 1912
# But also could be at different offsets. Let's try multiple mappings.

# Method 1: Direct parameter number mapping (reg = group*100 + param)
print("\n[Method 1] Registers 1900-1920 (group 19):")
r = c.read_holding_registers(address=1900, count=20, device_id=1)
if hasattr(r, 'registers'):
    for i, v in enumerate(r.registers):
        print(f"  Reg {1900+i} (P19.{i:02d}): {v}")
else:
    print(f"  Error: {r}")

# Method 2: Some ABB drives use (group-1)*256 + index or other schemes
print("\n[Method 2] Registers 1800-1830:")
r2 = c.read_holding_registers(address=1800, count=30, device_id=1)
if hasattr(r2, 'registers'):
    for i, v in enumerate(r2.registers):
        if v != 0:
            print(f"  Reg {1800+i}: {v}")
    if all(v == 0 for v in r2.registers):
        print("  (all zeros)")
else:
    print(f"  Error: {r2}")

# Method 3: Some use base 2000 area
print("\n[Method 3] Registers 2000-2030:")
r3 = c.read_holding_registers(address=2000, count=30, device_id=1)
if hasattr(r3, 'registers'):
    for i, v in enumerate(r3.registers):
        print(f"  Reg {2000+i}: {v}")
else:
    print(f"  Error: {r3}")

# Method 4: Try 2100 area
print("\n[Method 4] Registers 2100-2130:")
r4 = c.read_holding_registers(address=2100, count=30, device_id=1)
if hasattr(r4, 'registers'):
    for i, v in enumerate(r4.registers):
        print(f"  Reg {2100+i}: {v}")
else:
    print(f"  Error: {r4}")

# Method 5: Broad scan for all non-zero registers in range 1000-4000
print("\n[Full Scan] All non-zero registers 1000-4000:")
for base in range(1000, 4000, 100):
    r5 = c.read_holding_registers(address=base, count=100, device_id=1)
    if hasattr(r5, 'registers'):
        for i, v in enumerate(r5.registers):
            if v != 0:
                print(f"  Reg {base+i}: {v}")

# Now check: what's the current status word?
print("\n[Status Check] Fieldbus data registers 0-4:")
r6 = c.read_holding_registers(address=0, count=5, device_id=1)
if hasattr(r6, 'registers'):
    for i, v in enumerate(r6.registers):
        labels = ['Control Word', 'Speed Ref', 'Status Word', 'Actual Speed', 'Current']
        print(f"  Reg {i} ({labels[i]}): {v} (0x{v:04X})")

c.close()
print("\nDone.")
