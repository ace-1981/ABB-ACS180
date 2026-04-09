"""Debug: scan all register ranges to find correct ACS180 addresses"""
from pymodbus.client import ModbusSerialClient
import time

c = ModbusSerialClient(port='COM4', baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=2)
if not c.connect():
    print("Cannot open COM4")
    exit()

print("=" * 60)
print("  ACS180 REGISTER SCAN")
print("=" * 60)

# 1. Read first 20 registers
print("\n[1] HOLDING REGISTERS 0-19:")
r = c.read_holding_registers(address=0, count=20, device_id=1)
if hasattr(r, 'registers'):
    for i, v in enumerate(r.registers):
        marker = " <-- non-zero!" if v != 0 else ""
        print(f"  Reg {i:3d}: {v:5d}  (0x{v:04X}){marker}")

# 2. Write RUN to reg 0 and check if it sticks
print("\n[2] WRITE TEST - CW_RUN (0x047F) to reg 0:")
w = c.write_register(address=0, value=0x047F, device_id=1)
print(f"  Write error: {w.isError()}")
time.sleep(0.3)
r2 = c.read_holding_registers(address=0, count=5, device_id=1)
if hasattr(r2, 'registers'):
    for i, v in enumerate(r2.registers):
        print(f"  Reg {i:3d}: {v:5d}  (0x{v:04X})")

# 3. Scan wider ranges for non-zero data
print("\n[3] SCANNING WIDER REGISTER RANGES:")
for base in range(0, 10000, 100):
    try:
        r3 = c.read_holding_registers(address=base, count=10, device_id=1)
        if hasattr(r3, 'registers') and any(v != 0 for v in r3.registers):
            vals = [f"{v}" for v in r3.registers]
            print(f"  Regs {base:5d}-{base+9}: {vals}")
    except:
        pass

# 4. Try INPUT registers too (function code 04)
print("\n[4] INPUT REGISTERS (FC04) 0-19:")
r4 = c.read_input_registers(address=0, count=20, device_id=1)
if hasattr(r4, 'registers'):
    for i, v in enumerate(r4.registers):
        marker = " <-- non-zero!" if v != 0 else ""
        print(f"  Reg {i:3d}: {v:5d}  (0x{v:04X}){marker}")
else:
    print(f"  No response or error: {r4}")

c.close()
print("\nDone.")
