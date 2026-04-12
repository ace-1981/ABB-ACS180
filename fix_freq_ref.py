"""THE FIX: Set P28.11=8 (EFB ref1) for frequency reference.
Also try CW without bit 10 to use EXT1.
Correct addr = group*100 + index - 1
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

def addr(g, i): return g * 100 + i - 1
def read_p(g, i):
    try:
        res = client.read_holding_registers(address=addr(g,i), count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0: return res.registers[0]
    except: pass
    return None
def write_p(g, i, v):
    try:
        res = client.write_register(address=addr(g,i), value=v, device_id=1)
        return not res.isError() if hasattr(res, 'isError') else False
    except: return False
def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

# Stop motor
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(1)

print("=== Current Frequency Reference Chain ===")
print(f"  P19.12 (Ext1 control mode) = {read_p(19,12)}")
print(f"  P19.14 (Ext2 control mode) = {read_p(19,14)}")
print(f"  P28.11 (EXT1 freq ref1) = {read_p(28,11)}")
print(f"  P28.12 (EXT1 freq ref2) = {read_p(28,12)}")
print(f"  P28.18 (EXT2 freq ref1) = {read_p(28,18)}")
print(f"  P28.19 (EXT2 freq ref2) = {read_p(28,19)}")

# FIX P28.11 = 8 (EFB ref1)
print("\n=== FIXING P28.11 = 8 (EFB ref1) ===")
ok = write_p(28, 11, 8)
print(f"  Write: {'OK' if ok else 'FAILED'}")
print(f"  Verify: P28.11 = {read_p(28,11)}")

# FIX P28.12 = 0 (Zero - don't add anything)
# Check what P28.12 is
v28_12 = read_p(28, 12)
print(f"  P28.12 = {v28_12}")

# Also try EXT2 freq ref
print("\n  Setting P28.18 = 8 (EFB ref1)...")
ok = write_p(28, 18, 8)
print(f"  Write: {'OK' if ok else 'FAILED'}")
print(f"  Verify: P28.18 = {read_p(28,18)}")

# Try P28.19 too
print(f"  Setting P28.19 = 8...")
ok = write_p(28, 19, 8)
print(f"  Write: {'OK' if ok else 'FAILED'}")

# Test 1: EXT2 mode (CW=0x047F, bit10=1)
print("\n\n=== TEST 1: EXT2 mode (CW=0x047F) ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(5)

for i in range(10):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        efb1 = signed(read_p(3, 9))
        print(f"  t={i+1:2d}s: SW=0x{sw:04X} Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

# Stop
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)

# Test 2: EXT1 mode (CW=0x007F, bit10=0)
print("\n=== TEST 2: EXT1 mode (CW=0x007F, bit10=0) ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)
client.write_register(address=0, value=0x007F, device_id=1)
time.sleep(5)

for i in range(10):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        efb1 = signed(read_p(3, 9))
        print(f"  t={i+1:2d}s: SW=0x{sw:04X} Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

# Ramp test with best CW
print("\n=== Speed Ramp (EXT1 mode) ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(5)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        efb1 = signed(read_p(3, 9))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

client.write_register(address=0, value=0x047E, device_id=1)
print("\nMotor stopped.")
client.close()
