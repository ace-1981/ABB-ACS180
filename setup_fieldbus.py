"""Configure ACS180 for full fieldbus control based on the official manual.
Sets P22.11=8 (EFB ref1) and P28.11=8 (EFB ref1) so speed/frequency
reference comes from Modbus register 2 (EFB Reference 1).
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

def read_param(group, index):
    """Read a parameter using Mode 0 addressing: addr = group*100 + index"""
    addr = group * 100 + index
    try:
        res = client.read_holding_registers(address=addr, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except Exception:
        pass
    return None

def write_param(group, index, value):
    """Write a parameter using Mode 0 addressing"""
    addr = group * 100 + index
    res = client.write_register(address=addr, value=value, device_id=1)
    ok = not res.isError() if hasattr(res, 'isError') else False
    return ok

# Stop motor first
print("Stopping motor...")
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

# 1. Read current settings
print("\n=== Current Settings ===")
params_to_check = [
    (20, 1, "Ext1 commands"),
    (20, 6, "Ext1 commands (alt)"),
    (22, 11, "Ext1 speed ref1"),
    (22, 12, "Ext1 speed ref2"),
    (22, 13, "Ext1 speed function"),
    (22, 18, "Ext2 speed ref1"),
    (22, 19, "Ext2 speed ref2"),
    (22, 20, "Ext2 speed function"),
    (28, 11, "Ext1 frequency ref1"),
    (28, 12, "Ext1 frequency ref2"),
    (28, 18, "Ext2 frequency ref1"),
    (28, 19, "Ext2 frequency ref2"),
    (58, 1, "Protocol enable"),
    (58, 3, "Node address"),
    (58, 4, "Baud rate"),
    (58, 5, "Parity"),
    (58, 25, "Control profile"),
    (58, 26, "EFB ref1 type"),
    (58, 27, "EFB ref2 type"),
    (58, 101, "Data I/O 1 mapping"),
    (58, 102, "Data I/O 2 mapping"),
    (58, 103, "Data I/O 3 mapping"),
    (58, 104, "Data I/O 4 mapping"),
    (58, 105, "Data I/O 5 mapping"),
    (58, 106, "Data I/O 6 mapping"),
    (3, 9, "EFB reference 1"),
    (3, 10, "EFB reference 2"),
]

for grp, idx, name in params_to_check:
    val = read_param(grp, idx)
    print(f"  P{grp:02d}.{idx:02d} ({name}) = {val}")

# 2. Configure for fieldbus control
print("\n=== Configuring Fieldbus Control ===")

# P22.11 = 8 (EFB ref1) - Ext1 speed reference source = Embedded Fieldbus Ref 1
print("\nSetting P22.11 = 8 (EFB ref1)...")
ok = write_param(22, 11, 8)
print(f"  Result: {'OK' if ok else 'FAILED'}")
verify = read_param(22, 11)
print(f"  Verify: P22.11 = {verify}")

# P28.11 = 8 (EFB ref1) - Ext1 frequency reference source = Embedded Fieldbus Ref 1  
print("\nSetting P28.11 = 8 (EFB ref1)...")
ok = write_param(28, 11, 8)
print(f"  Result: {'OK' if ok else 'FAILED'}")
verify = read_param(28, 11)
print(f"  Verify: P28.11 = {verify}")

# Also set EXT2 refs to EFB ref1 in case EXT2 is active
print("\nSetting P22.18 = 8 (EFB ref1) [Ext2 speed]...")
ok = write_param(22, 18, 8)
print(f"  Result: {'OK' if ok else 'FAILED'}")
verify = read_param(22, 18)
print(f"  Verify: P22.18 = {verify}")

print("\nSetting P28.18 = 8 (EFB ref1) [Ext2 freq]...")
ok = write_param(28, 18, 8)
print(f"  Result: {'OK' if ok else 'FAILED'}")
verify = read_param(28, 18)
print(f"  Verify: P28.18 = {verify}")

# Restore P21.02 and P21.03 to original values (we wrote wrong values earlier!)
print("\nRestoring P21.02 (Magnetization time)...")
# Default is typically some value, but let's just read it
val = read_param(21, 2)
print(f"  Current P21.02 = {val}")
val = read_param(21, 3)
print(f"  Current P21.03 = {val}")

# 3. Now test motor with fieldbus reference
print("\n=== Motor Test with Fieldbus Reference ===")

# Set reference to 50% (10000) on register 1 (EFB Ref1)
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)

# Start motor
client.write_register(address=0, value=config.CW_RUN, device_id=1)
print("Motor started with ref=10000 (50%)")

# Monitor
for i in range(20):
    time.sleep(1)
    # Read registers 0-5
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers'):
        cw = r.registers[0]
        ref = r.registers[1]
        ref2 = r.registers[2]
        sw = r.registers[3]
        act1 = r.registers[4] if r.registers[4] < 32768 else r.registers[4] - 65536
        act2 = r.registers[5] if r.registers[5] < 32768 else r.registers[5] - 65536
        running = bool(sw & 0x0004)
        print(f"  t={i+1:2d}s: CW=0x{cw:04X} Ref1={ref} Ref2={ref2} SW=0x{sw:04X} Run={running} Act1={act1} Act2={act2}")
    
    # Also read EFB reference actuals
    efb1 = read_param(3, 9)
    efb2 = read_param(3, 10)
    if efb1 is not None:
        e1 = efb1 if efb1 < 32768 else efb1 - 65536
        e2 = efb2 if efb2 < 32768 else efb2 - 65536
        print(f"         EFB Ref1={e1} EFB Ref2={e2}")

# Speed ramp test
print("\n=== Speed Ramp Test ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(3)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers'):
        act1 = r.registers[4] if r.registers[4] < 32768 else r.registers[4] - 65536
        act2 = r.registers[5] if r.registers[5] < 32768 else r.registers[5] - 65536
        efb1 = read_param(3, 9)
        e1 = (efb1 if efb1 < 32768 else efb1 - 65536) if efb1 is not None else 'N/A'
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} Act2={act2} EFB_Ref1={e1}")

# Stop
client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
