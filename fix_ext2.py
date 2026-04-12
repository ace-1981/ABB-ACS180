"""Check EXT1 vs EXT2 - CW bit 10 and reference sources.
Using CORRECT address offset: addr = group*100 + index - 1
"""
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

def addr(group, index):
    return group * 100 + index - 1

def read_p(group, index):
    a = addr(group, index)
    try:
        res = client.read_holding_registers(address=a, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except:
        pass
    return None

def write_p(group, index, value):
    a = addr(group, index)
    try:
        res = client.write_register(address=a, value=value, device_id=1)
        return not res.isError() if hasattr(res, 'isError') else False
    except:
        return False

def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

# Stop motor
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

print("=== Control Word Analysis ===")
cw = 0x047F
print(f"CW = 0x{cw:04X} = {cw:016b}")
print(f"  Bit 10 (Ext1/Ext2 sel) = {(cw>>10)&1}")
if (cw >> 10) & 1:
    print("  >>> Drive is in EXT2 mode!")
else:
    print("  >>> Drive is in EXT1 mode!")

print("\n=== Reference Sources (correct -1 offset) ===")
print(f"  P19.11 (Ext1/Ext2 sel) = {read_p(19, 11)}")
print(f"  P22.11 (EXT1 speed ref1) = {read_p(22, 11)}")
print(f"  P22.12 (EXT1 speed ref2) = {read_p(22, 12)}")
print(f"  P22.13 (EXT1 speed func) = {read_p(22, 13)}")
print(f"  P22.18 (EXT2 speed ref1) = {read_p(22, 18)}")
print(f"  P22.19 (EXT2 speed ref2) = {read_p(22, 19)}")  
print(f"  P22.20 (EXT2 speed func) = {read_p(22, 20)}")
print(f"  P28.11 (EXT1 freq ref1)  = {read_p(28, 11)}")
print(f"  P28.18 (EXT2 freq ref1)  = {read_p(28, 18)}")

# KEY: Check if P22.18 is 0 (Zero) - THIS would explain the problem!
v22_18 = read_p(22, 18)
v28_18 = read_p(28, 18)
print(f"\n  >>> P22.18 = {v22_18} {'(Zero = NO reference!)' if v22_18 == 0 else '(EFB ref1)' if v22_18 == 8 else ''}")
print(f"  >>> P28.18 = {v28_18} {'(Zero = NO reference!)' if v28_18 == 0 else '(EFB ref1)' if v28_18 == 8 else ''}")

# FIX: Set P22.18 and P28.18 to 8 (EFB ref1)
if v22_18 != 8:
    print(f"\n  Fixing P22.18 = 8 (EFB ref1)...")
    ok = write_p(22, 18, 8)
    print(f"  Result: {'OK' if ok else 'FAILED'}")
    print(f"  Verify: P22.18 = {read_p(22, 18)}")

if v28_18 != 8:
    print(f"\n  Fixing P28.18 = 8 (EFB ref1)...")
    ok = write_p(28, 18, 8)
    print(f"  Result: {'OK' if ok else 'FAILED'}")
    print(f"  Verify: P28.18 = {read_p(28, 18)}")

# Also make sure P20.01 = 14 (EFB) and P20.06 (Ext2 commands) = 14
print(f"\n  P20.01 (Ext1 commands) = {read_p(20, 1)} (14=EFB)")
print(f"  P20.06 (Ext2 commands) = {read_p(20, 6)}")
v_20_06 = read_p(20, 6)
if v_20_06 != 14:
    print(f"  Fixing P20.06 = 14 (EFB)...")
    ok = write_p(20, 6, 14)
    print(f"  Result: {'OK' if ok else 'FAILED'}")
    print(f"  Verify: P20.06 = {read_p(20, 6)}")

# Now test motor
print("\n=== Motor Test ===")
# Set reference to 50% (10000)
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.3)

# Check EFB reference 
efb1 = signed(read_p(3, 9))
print(f"  P03.09 (EFB Ref1) = {efb1}")

# Start
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(3)

print("\n  Motor running, monitoring:")
for i in range(15):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        running = bool(sw & 0x0004)
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        efb1 = signed(read_p(3, 9))
        print(f"    t={i+1:2d}s: SW=0x{sw:04X} Run={running} Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

# Ramp test
print("\n=== Speed Ramp ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(4)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        efb1 = signed(read_p(3, 9))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
