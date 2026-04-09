"""Debug: full parameter scan to find ACS180 control mode settings"""
from pymodbus.client import ModbusSerialClient
import time

c = ModbusSerialClient(port='COM4', baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=2)
if not c.connect():
    print("Cannot open COM4")
    exit()

print("=" * 60)
print("  ACS180 FULL PARAMETER SCAN")
print("=" * 60)

# Scan all register ranges in blocks of 10
print("\nScanning ALL non-zero registers 0-9999...")
found_ranges = []
for base in range(0, 10000, 10):
    try:
        r = c.read_holding_registers(address=base, count=10, device_id=1)
        if hasattr(r, 'registers') and any(v != 0 for v in r.registers):
            found_ranges.append((base, r.registers))
    except:
        pass

for base, regs in found_ranges:
    for i, v in enumerate(regs):
        if v != 0:
            addr = base + i
            print(f"  Reg {addr:5d}: {v:6d}  (0x{v:04X})")

# Now specifically check parameter group 19 (control mode) and 58 (Modbus)
# ABB ACS180: param XX.YY -> register might be at XX*100+YY or other mapping
print("\n" + "=" * 60)
print("  KEY AREAS FOR CONTROL CONFIG")
print("=" * 60)

# Check around 1900 (group 19 - operating mode)
print("\n[Group 19 area - Operating Mode] Regs 1900-1920:")
r19 = c.read_holding_registers(address=1900, count=20, device_id=1)
if hasattr(r19, 'registers'):
    for i, v in enumerate(r19.registers):
        print(f"  Reg {1900+i}: {v:5d}  (0x{v:04X})")
else:
    print(f"  Error: {r19}")

# Check around 5800 (group 58 - Modbus settings)
print("\n[Group 58 area - Modbus/Comm] Regs 5800-5820:")
r58 = c.read_holding_registers(address=5800, count=20, device_id=1)
if hasattr(r58, 'registers'):
    for i, v in enumerate(r58.registers):
        print(f"  Reg {5800+i}: {v:5d}  (0x{v:04X})")
else:
    print(f"  Error: {r58}")

# Also try register 50001+ style (Modbus standard sometimes uses offsets)
print("\n[Trying write+readback test on reg 1 (speed ref)]:")
print(f"  Before: ", end="")
rb = c.read_holding_registers(address=1, count=1, device_id=1)
if hasattr(rb, 'registers'):
    print(f"{rb.registers[0]}")
w = c.write_register(address=1, value=5000, device_id=1)  # 50%
print(f"  Write 5000 to reg 1: error={w.isError()}")
time.sleep(0.3)
ra = c.read_holding_registers(address=1, count=1, device_id=1)
if hasattr(ra, 'registers'):
    print(f"  After:  {ra.registers[0]}")
    if ra.registers[0] == 5000:
        print("  >> Write STICKS - register is writable")
    else:
        print("  >> Write did NOT stick - register is read-only or overwritten by drive")

c.close()
print("\nDone.")
