"""Full diagnostic: check params, start motor, read real P01 values."""
from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(
    port="COM4", baudrate=19200, parity="E", stopbits=1, bytesize=8, timeout=2.0
)
if not client.connect():
    print("ERROR: Cannot open COM4!")
    exit(1)

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

# Check key parameters
print("=== Key Parameters ===")
params = [
    (28,11,"EXT1 freq ref1 (should be 8=EFB)"),
    (28,18,"EXT2 freq ref1"),
    (22,11,"EXT1 speed ref1 (should be 8=EFB)"),
    (22,18,"EXT2 speed ref1 (should be 8=EFB)"),
    (20,1,"EXT1 commands (should be 14=EFB)"),
    (20,6,"EXT2 commands (should be 14=EFB)"),
    (19,12,"EXT1 ctrl mode"),
    (19,14,"EXT2 ctrl mode"),
    (58,101,"Data I/O Map: Reg0"),
    (58,102,"Data I/O Map: Reg1"),
    (58,103,"Data I/O Map: Reg2"),
    (58,104,"Data I/O Map: Reg3"),
    (58,105,"Data I/O Map: Reg4"),
    (58,106,"Data I/O Map: Reg5"),
]
for g, i, name in params:
    v = read_p(g, i)
    print(f"  P{g:02d}.{i:02d} = {signed(v) if v is not None else 'N/A':>6}  ({name})")

# Read Data I/O registers raw
print("\n=== Data I/O Registers (addr 0-5) ===")
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    names = ["CW", "Ref1", "Ref2", "SW", "Act1", "Act2"]
    for n, v in zip(names, r.registers):
        print(f"  Reg {n}: {v} (0x{v:04X}, signed={signed(v)})")

# Start motor with known working method
print("\n=== Starting Motor (EXT2, CW=0x047F, Ref=10000) ===")
# Write ref first
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
# Write CW
client.write_register(address=0, value=0x047F, device_id=1)

# Monitor for 10 seconds
print("Monitoring for 10 seconds...")
for i in range(10):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    p0107 = read_p(1, 7)   # Output frequency
    p0108 = read_p(1, 8)   # Output current
    p0101 = read_p(1, 1)   # Motor speed
    p0309 = read_p(3, 9)   # EFB ref1 actual
    
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        cw, ref1, ref2, sw, act1, act2 = r.registers
        print(f"  t={i+1:2d}s: SW=0x{sw:04X} Act1={signed(act1):6d} Act2={signed(act2):6d} | "
              f"P01.07(freq)={signed(p0107)} P01.08(curr)={signed(p0108)} "
              f"P01.01(speed)={signed(p0101)} P03.09(efb)={signed(p0309)}")

# Try different ref values
print("\n=== Speed ramp ===")
for pct in [25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(3)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    p0107 = read_p(1, 7)
    p0108 = read_p(1, 8)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1:6d} P01.07={signed(p0107)} P01.08={signed(p0108)}")

# Stop
print("\n=== Stopping ===")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(1)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  SW=0x{r.registers[3]:04X} Act1={signed(r.registers[4])} Act2={signed(r.registers[5])}")

client.close()
print("Done.")
