"""Fix params that reverted + start motor + verify spinning."""
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
def write_p(g, i, v):
    try:
        r = client.write_register(address=addr(g,i), value=v, device_id=1)
        return not r.isError()
    except: return False

# Stop motor first
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(0.5)

# Fix all reverted params
fixes = [
    (28, 11, 8,  "EXT1 freq ref1 = EFB"),
    (22, 18, 8,  "EXT2 speed ref1 = EFB"),
    (20,  6, 14, "EXT2 commands = EFB"),
]

print("=== Fixing Params ===")
for g, i, val, desc in fixes:
    before = read_p(g, i)
    ok = write_p(g, i, val)
    after = read_p(g, i)
    status = "OK" if ok and after == val else "FAILED"
    print(f"  P{g:02d}.{i:02d}: {signed(before)} -> {val} ({desc}) [{status}]")

# Verify all key params
print("\n=== Verify All ===")
checks = [
    (28,11,8), (22,11,8), (22,18,8), (20,1,14), (20,6,14),
]
all_ok = True
for g, i, expected in checks:
    v = read_p(g, i)
    ok = "OK" if v == expected else f"WRONG (got {signed(v)})"
    if v != expected: all_ok = False
    print(f"  P{g:02d}.{i:02d} = {signed(v):>4} (expect {expected}) [{ok}]")

if not all_ok:
    print("\nSome params WRONG! Motor may not spin.")

# Start motor
print("\n=== Starting Motor ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=0x047F, device_id=1)

# Monitor
print("Monitoring...")
for i in range(15):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    p0107 = read_p(1, 7)
    p0108 = read_p(1, 8)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        sw, act1, act2 = r.registers[3], signed(r.registers[4]), signed(r.registers[5])
        running = "RUN" if sw & 0x0004 else "STOP"
        print(f"  t={i+1:2d}s: [{running}] SW=0x{sw:04X} Act1={act1:6d} Freq={signed(p0107):>4} Curr={signed(p0108):>4}")
        if signed(p0107) is not None and isinstance(signed(p0107), int) and signed(p0107) > 10:
            print(f"  >>> MOTOR SPINNING! freq={signed(p0107)/10.0:.1f}Hz")

# Speed ramp
print("\n=== Speed Ramp ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(4)
    p0107 = read_p(1, 7)
    p0108 = read_p(1, 8)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    act1 = signed(r.registers[4]) if hasattr(r, 'registers') else 'N/A'
    print(f"  {pct:3d}% (ref={val:5d}): Freq={signed(p0107)} Curr={signed(p0108)} Act1={act1}")

# Stop
print("\n=== Stop ===")
client.write_register(address=0, value=0x047E, device_id=1)
client.close()
print("Done.")
