"""Quick targeted scan of ACS180 key registers"""
from pymodbus.client import ModbusSerialClient
import time

c = ModbusSerialClient(port='COM4', baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=0.5)
if not c.connect():
    print("Cannot open COM4")
    exit()

print("=" * 60)
print("  ACS180 TARGETED REGISTER CHECK")
print("=" * 60)

# First the fieldbus data registers (0-9)
print("\n[Fieldbus Data Registers 0-9]:")
r = c.read_holding_registers(address=0, count=10, device_id=1)
if hasattr(r, 'registers'):
    labels = ['Control Word', 'Speed Ref', 'Status Word', 'Actual Speed', 
              'Actual Current', 'Reg5', 'Reg6', 'Reg7', 'Reg8', 'Reg9']
    for i, v in enumerate(r.registers):
        print(f"  Reg {i}: {v:6d} (0x{v:04X})  [{labels[i]}]")

# Check known non-zero areas from previous scan
key_areas = [
    (2000, 20, "Group 20 - Params?"),
    (2100, 20, "Group 21 - Params?"),
    (3100, 20, "Group 31 - Params?"),
    (1900, 20, "Group 19 - Operating Mode?"),
    (5800, 20, "Group 58 - Modbus/Comm?"),
]

for base, count, label in key_areas:
    print(f"\n[{label}] Regs {base}-{base+count-1}:")
    r = c.read_holding_registers(address=base, count=count, device_id=1)
    if hasattr(r, 'registers'):
        for i, v in enumerate(r.registers):
            if v != 0:
                print(f"  Reg {base+i}: {v:6d} (0x{v:04X})")
        if all(v == 0 for v in r.registers):
            print("  (all zeros)")
    else:
        print(f"  Error/No response: {r}")

# Write test: can we change speed ref?
print("\n[Write Test - Speed Ref at Reg 1]:")
r1 = c.read_holding_registers(address=1, count=1, device_id=1)
before = r1.registers[0] if hasattr(r1, 'registers') else '?'
print(f"  Before: {before}")
c.write_register(address=1, value=5000, device_id=1)
time.sleep(0.2)
r1b = c.read_holding_registers(address=1, count=1, device_id=1)
after = r1b.registers[0] if hasattr(r1b, 'registers') else '?'
print(f"  After write 5000: {after}")
if after == 5000:
    print("  >>> WRITE WORKS on reg 1!")
else:
    print(f"  >>> Write did not stick (drive overwrites it)")

# Check status word in detail
print("\n[Status Word Analysis (Reg 2)]:")
r2 = c.read_holding_registers(address=2, count=1, device_id=1)
if hasattr(r2, 'registers'):
    sw = r2.registers[0]
    print(f"  Raw: {sw} (0x{sw:04X})")
    print(f"  Bit 0 (Ready to switch on): {bool(sw & 0x0001)}")
    print(f"  Bit 1 (Switched on):        {bool(sw & 0x0002)}")
    print(f"  Bit 2 (Operation enabled):   {bool(sw & 0x0004)}")
    print(f"  Bit 3 (Fault):               {bool(sw & 0x0008)}")
    print(f"  Bit 4 (Voltage enabled):     {bool(sw & 0x0010)}")
    print(f"  Bit 5 (Quick stop):          {bool(sw & 0x0020)}")
    print(f"  Bit 6 (Switch on disabled):  {bool(sw & 0x0040)}")
    print(f"  Bit 7 (Warning):             {bool(sw & 0x0080)}")
    if sw == 0:
        print("\n  >>> STATUS WORD = 0 means drive is NOT controlled via Modbus!")
        print("  >>> You need to configure the drive panel:")
        print("  >>>   1. Set drive to REMOTE mode (LOC/REM button)")
        print("  >>>   2. Set EXT1/EXT2 command source = Fieldbus")
        print("  >>>   3. Set speed reference = Fieldbus")

c.close()
print("\nDone.")
