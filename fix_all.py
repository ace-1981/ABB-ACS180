"""Fix all fieldbus parameters based on the ACS180 manual."""
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
    addr = group * 100 + index
    try:
        res = client.read_holding_registers(address=addr, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except:
        pass
    return None

def write_param(group, index, value):
    addr = group * 100 + index
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

print("=== Step 1: Read scaling parameters ===")
print(f"  P46.01 (Speed scaling) = {read_param(46, 1)}")
print(f"  P46.02 (Frequency scaling) = {read_param(46, 2)}")
print(f"  P46.03 (Torque scaling) = {read_param(46, 3)}")

print("\n=== Step 2: Fix P58.26 (EFB ref1 type) ===")
print(f"  Current P58.26 = {read_param(58, 26)} (should be 0=Speed or frequency)")
print("  Setting P58.26 = 0 (Speed or frequency)...")
ok = write_param(58, 26, 0)
print(f"  Result: {'OK' if ok else 'FAILED'}")
print(f"  Verify: P58.26 = {read_param(58, 26)}")

# Also fix P58.27 - should be Transparent(1) or General(2) for ref2
print(f"\n  Current P58.27 = {read_param(58, 27)}")

print("\n=== Step 3: Refresh EFB settings (P58.06) ===")
# P58.06 Communication control - usually value to refresh
v58_06 = read_param(58, 6)
print(f"  Current P58.06 = {v58_06}")
# Try writing "Refresh settings" value (typically 1)
ok = write_param(58, 6, 1)
print(f"  Write P58.06=1 (Refresh): {'OK' if ok else 'FAILED'}")
time.sleep(2)

print("\n=== Step 4: Read P03.09 after changes ===")
efb1 = read_param(3, 9)
print(f"  P03.09 (EFB reference 1) = {signed(efb1)}")

# Write ref to register 1 and check
print("\n=== Step 5: Write reference and test ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.5)
efb1 = read_param(3, 9)
print(f"  Wrote 10000 to reg 1 -> P03.09 = {signed(efb1)}")

# Also try writing to reg 2
client.write_register(address=2, value=5000, device_id=1)
time.sleep(0.5)
efb2 = read_param(3, 10)
print(f"  Wrote 5000 to reg 2 -> P03.10 = {signed(efb2)}")

# Now try to access P58.101-P58.106 using Mode 1 addressing
# First, check current mode
mode = read_param(58, 33)
print(f"\n=== Step 6: Check Data I/O mapping ===")
print(f"  P58.33 (Addressing mode) = {mode}")

if mode == 0:
    # Mode 0: groups 1-99, indexes 1-99. Can't access P58.101+
    # Switch to Mode 1 temporarily
    print("  Switching to Mode 1 to read P58.101+...")
    ok = write_param(58, 33, 1)
    print(f"  Write P58.33=1: {'OK' if ok else 'FAILED'}")
    time.sleep(0.5)
    
    # Refresh
    write_param(58, 6, 1)
    time.sleep(1)
    
    # Mode 1: address = 256*group + index
    # P58.101 -> 256*58 + 101 = 14949
    for idx in range(101, 115):
        addr = 256 * 58 + idx
        try:
            res = client.read_holding_registers(address=addr, count=1, device_id=1)
            if hasattr(res, 'registers') and len(res.registers) > 0:
                v = res.registers[0]
                print(f"  P58.{idx} (Data I/O {idx-100}) = {v}")
            else:
                print(f"  P58.{idx} (Data I/O {idx-100}) = ERROR")
        except Exception as e:
            print(f"  P58.{idx} (Data I/O {idx-100}) = EXCEPTION: {e}")
    
    # Also re-read P22.11 in Mode 1
    addr22_11 = 256 * 22 + 11
    try:
        res = client.read_holding_registers(address=addr22_11, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            print(f"  P22.11 (Mode 1) = {res.registers[0]}")
    except:
        print(f"  P22.11 (Mode 1) = ERROR")
    
    # Switch back to Mode 0
    addr58_33_mode1 = 256 * 58 + 33
    try:
        client.write_register(address=addr58_33_mode1, value=0, device_id=1)
        print("  Switched back to Mode 0")
    except:
        # Try Mode 0 address too
        write_param(58, 33, 0)
        print("  Switched back to Mode 0 (fallback)")
    
    time.sleep(0.5)
    write_param(58, 6, 1)
    time.sleep(1)

# Now test motor
print("\n=== Step 7: Motor Test ===")
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
print("Motor started, ref=10000")

for i in range(15):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        ref = r.registers[1]
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        running = bool(sw & 0x0004)
        efb1 = signed(read_param(3, 9))
        p0107 = signed(read_param(1, 7))
        print(f"  t={i+1:2d}s: Ref={ref} Run={running} Act1={act1} Act2={act2} EFB1={efb1} P01.07={p0107}")

# Ramp test
print("\n=== Speed Ramp ===")
for pct in [10, 30, 50, 80]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(4)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        efb1 = signed(read_param(3, 9))
        p0107 = signed(read_param(1, 7))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} EFB1={efb1} P01.07={p0107}")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
