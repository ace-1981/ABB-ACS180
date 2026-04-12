"""Test reverse direction methods for ACS180."""
from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(
    port="COM4", baudrate=19200, parity="E", stopbits=1, bytesize=8, timeout=2.0
)
if not client.connect():
    print("ERROR: Cannot open COM4!"); exit(1)

def addr(g, i): return g * 100 + i - 1
def signed(v):
    if v is None: return 'N/A'
    return v if v < 0x8000 else v - 0x10000
def read_p(g, i):
    try:
        r = client.read_holding_registers(address=addr(g,i), count=1, device_id=1)
        if hasattr(r, 'registers') and len(r.registers) > 0: return r.registers[0]
    except: pass
    return None
def read_all():
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        cw, ref1, ref2, sw, act1, act2 = r.registers
        print(f"  CW=0x{cw:04X} Ref1={signed(ref1):6d} SW=0x{sw:04X} Act1={signed(act1):6d} Act2={signed(act2):6d}")
        return sw
    return None

# Stop first
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(1)

# Check relevant direction params
print("=== Direction Parameters ===")
for g, i, desc in [
    (22, 14, "EXT1 negative speed"),
    (22, 15, "EXT1 pos speed limit"),
    (22, 16, "EXT1 neg speed limit"),
    (28, 14, "EXT1 negative freq"),
    (28, 15, "EXT1 pos freq limit"),
    (28, 16, "EXT1 neg freq limit"),
    (22, 21, "EXT2 negative speed"),
    (28, 21, "EXT2 negative freq"),
]:
    v = read_p(g, i)
    print(f"  P{g:02d}.{i:02d} = {signed(v) if v is not None else 'N/A':>6}  ({desc})")

# Method 1: CW bit 11 (what we tried)
print("\n=== Test 1: CW bit 11 = 1 (0x0C7F) ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=0x0C7F, device_id=1)  # bit 11 set
time.sleep(3)
read_all()
p0107 = read_p(1, 7)
print(f"  P01.07 (freq) = {signed(p0107)}")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)

# Method 2: Negative reference (two's complement)
print("\n=== Test 2: Negative reference (-10000 = 0xD8F0) ===")
neg_ref = 0x10000 - 10000  # = 55536 = 0xD8F0
print(f"  Writing Ref1 = {neg_ref} (0x{neg_ref:04X}, signed = {signed(neg_ref)})")
client.write_register(address=1, value=neg_ref, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=0x047F, device_id=1)  # normal CW, no bit 11
time.sleep(3)
read_all()
p0107 = read_p(1, 7)
p0101 = read_p(1, 1)
print(f"  P01.07 (freq) = {signed(p0107)}")
print(f"  P01.01 (speed) = {signed(p0101)}")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)

# Method 3: Both bit 11 + negative ref
print("\n=== Test 3: CW bit 11 + Negative reference ===")
client.write_register(address=1, value=neg_ref, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=0x0C7F, device_id=1)
time.sleep(3)
read_all()
p0107 = read_p(1, 7)
print(f"  P01.07 (freq) = {signed(p0107)}")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)

# Method 4: Try enabling negative speed first
print("\n=== Trying to enable negative speed/freq ===")
for g, i, val, desc in [
    (22, 14, 1, "EXT1 neg speed enable"),
    (28, 14, 1, "EXT1 neg freq enable"),
    (22, 21, 1, "EXT2 neg speed enable"),
    (28, 21, 1, "EXT2 neg freq enable"),
]:
    try:
        r = client.write_register(address=addr(g,i), value=val, device_id=1)
        ok = not r.isError()
    except: ok = False
    after = read_p(g, i)
    print(f"  P{g:02d}.{i:02d} = {val} ({desc}) [{'OK' if ok else 'FAIL'}] verify={signed(after) if after is not None else 'N/A'}")

# Test again with negative ref after enabling
print("\n=== Test 4: Negative ref after enabling ===")
client.write_register(address=1, value=neg_ref, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(4)
read_all()
p0107 = read_p(1, 7)
p0101 = read_p(1, 1)
print(f"  P01.07 (freq) = {signed(p0107)}")
print(f"  P01.01 (speed) = {signed(p0101)}")

# Monitor
for i in range(5):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers'):
        act1 = signed(r.registers[4])
        print(f"  t={i+1}s: Act1={act1}")

client.write_register(address=0, value=0x047E, device_id=1)
print("\nStopped.")
client.close()
