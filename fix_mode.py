"""Fix: Change motor control mode from Scalar to Vector,
so drive uses speed reference chain (P22) instead of frequency chain (P28).
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

# Read motor control mode params
print("=== Motor Control Mode ===")
print(f"  P99.04 (Motor ctrl mode) = {read_p(99, 4)}")
print(f"  P99.05 = {read_p(99, 5)}")
print(f"  P19.01 (Actual op mode) = {read_p(19, 1)}")
print(f"  P19.12 (Ext1 ctrl mode) = {read_p(19, 12)}")
print(f"  P19.14 (Ext2 ctrl mode) = {read_p(19, 14)}")
print(f"  P19.16 (Local ctrl mode) = {read_p(19, 16)}")

# P99.04 values: 0=Scalar, 1=Vector? Let's try
# Or P19.12/P19.14 values: 0=Speed, 1=Torque?, 2=Scalar?

# Try changing P19.14 (Ext2 control mode) from 2 to 0 (Speed)
print("\n=== Change Ext2 to Speed mode ===")
print("  Setting P19.14 = 0 (Speed)...")
ok = write_p(19, 14, 0)
print(f"  Result: {'OK' if ok else 'FAILED'}")
print(f"  Verify: P19.14 = {read_p(19, 14)}")

# Also try Ext1
print("  Setting P19.12 = 0 (Speed)...")
ok = write_p(19, 12, 0)
print(f"  Result: {'OK' if ok else 'FAILED'}")
print(f"  Verify: P19.12 = {read_p(19, 12)}")

# If P99.04 exists, try changing it too
v99_04 = read_p(99, 4)
print(f"\n  P99.04 = {v99_04}")
if v99_04 is not None and v99_04 != 1:
    print(f"  Trying P99.04 = 1 (Vector)...")
    ok = write_p(99, 4, 1)
    print(f"  Result: {'OK' if ok else 'FAILED'}")
    print(f"  Verify: P99.04 = {read_p(99, 4)}")

# Test motor
print("\n=== Motor Test (EXT2, CW=0x047F) ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)
client.write_register(address=0, value=0x047F, device_id=1)

print("  Waiting 5s for ramp...")
time.sleep(5)

for i in range(15):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        p0106 = signed(read_p(1, 6))
        p0101 = signed(read_p(1, 1))
        efb1 = signed(read_p(3, 9))
        print(f"  t={i+6:2d}s: SW=0x{sw:04X} Act1={act1} Act2={act2} EFB1={efb1} P01.01={p0101} P01.06={p0106} P01.07={p0107} P01.08={p0108}")

# Ramp test
print("\n=== Speed Ramp ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(5)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        p0107 = signed(read_p(1, 7))
        p0108 = signed(read_p(1, 8))
        p0101 = signed(read_p(1, 1))
        efb1 = signed(read_p(3, 9))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} EFB1={efb1} P01.01={p0101} P01.07={p0107} P01.08={p0108}")

client.write_register(address=0, value=0x047E, device_id=1)
print("\nMotor stopped.")

# Show final mode
print(f"\nFinal P19.12 = {read_p(19, 12)}")
print(f"Final P19.14 = {read_p(19, 14)}")
print(f"Final P99.04 = {read_p(99, 4)}")

client.close()
