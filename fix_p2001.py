"""Set P20.01=14 (Embedded Fieldbus) - THIS is the key fix!
The manual says P20.01 must be 14 for fieldbus control.
Currently it's 1 (DI1 digital input) which means the drive ignores
our fieldbus Control Word for start/stop/direction commands.
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

def read_reg(addr):
    try:
        res = client.read_holding_registers(address=addr, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except:
        pass
    return None

def write_reg(addr, value):
    try:
        res = client.write_register(address=addr, value=value, device_id=1)
        return not res.isError() if hasattr(res, 'isError') else False
    except:
        return False

def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

# Stop motor first
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

print("=== BEFORE ===")
print(f"  P20.01 (Ext1 commands) = {read_reg(2001)}")
print(f"  P22.11 (Ext1 speed ref1) = {read_reg(2211)}")
print(f"  P28.11 (Ext1 freq ref1) = {read_reg(2811)}")
print(f"  P03.09 (EFB Ref1) = {signed(read_reg(309))}")

# Set P20.01 = 14 (Embedded fieldbus)
print("\n=== Setting P20.01 = 14 (Embedded Fieldbus) ===")
ok = write_reg(2001, 14)
print(f"  Result: {'OK' if ok else 'FAILED'}")
v = read_reg(2001)
print(f"  Verify: P20.01 = {v}")

if v != 14:
    print("  FAILED to set P20.01! Trying alternative...")
    # Maybe we need to stop first or something
    # Try writing again
    time.sleep(1)
    ok = write_reg(2001, 14)
    print(f"  Retry result: {'OK' if ok else 'FAILED'}")
    v = read_reg(2001)
    print(f"  Retry verify: P20.01 = {v}")

# Make sure P22.11 and P28.11 are still 8
v2211 = read_reg(2211)
v2811 = read_reg(2811)
print(f"\n  P22.11 = {v2211}")
print(f"  P28.11 = {v2811}")
if v2211 != 8:
    print("  Fixing P22.11 = 8...")
    write_reg(2211, 8)
if v2811 != 8:
    print("  Fixing P28.11 = 8...")
    write_reg(2811, 8)

# Now test motor
print("\n=== Motor Test ===")

# Set reference to 50% (10000)
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.5)

# Check EFB reference
efb1 = signed(read_reg(309))
print(f"  After writing 10000 to reg 1 -> P03.09 (EFB Ref1) = {efb1}")

# Start motor via Control Word
print("\n  Starting motor (CW=0x047F)...")
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(2)

# Monitor for 20 seconds
print("\n  Monitoring (check motor frequency!):")
for i in range(20):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        cw = r.registers[0]
        ref = r.registers[1]
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        running = bool(sw & 0x0004)
        
        efb1 = signed(read_reg(309))
        p0107 = signed(read_reg(107))  # output freq?
        p0108 = signed(read_reg(108))  # output current?

        print(f"    t={i+1:2d}s: CW=0x{cw:04X} SW=0x{sw:04X} Run={running} Ref={ref} Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

# Speed ramp
print("\n=== Speed Ramp Test ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(4)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        efb1 = signed(read_reg(309))
        p0107 = signed(read_reg(107))
        p0108 = signed(read_reg(108))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107} P01.08={p0108}")

# Stop
client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
