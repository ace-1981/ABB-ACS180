"""Try to change the speed reference source to Fieldbus on ACS180."""
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

def test_speed_ref():
    """Start motor, write speed ref, check if it sticks."""
    client.write_register(address=1, value=4000, device_id=1)
    time.sleep(0.1)
    client.write_register(address=0, value=config.CW_STOP, device_id=1)
    time.sleep(0.2)
    client.write_register(address=0, value=config.CW_RUN, device_id=1)
    time.sleep(1.5)
    res = client.read_holding_registers(address=0, count=6, device_id=1)
    ref_val = res.registers[1]
    sw = res.registers[3]
    # Read P01.07-09 for actual output
    p7 = client.read_holding_registers(address=107, count=3, device_id=1)
    actual = p7.registers if hasattr(p7, 'registers') else [0, 0, 0]
    client.write_register(address=0, value=config.CW_STOP, device_id=1)
    time.sleep(0.5)
    return ref_val, sw, actual

# Save original values
print("=== ACS180 Reference Source Fix ===\n")
orig_2102 = client.read_holding_registers(address=2102, count=1, device_id=1).registers[0]
print(f"Original Reg 2102 (Ref source) = {orig_2102}")

# First test with current config
print("\n[TEST 0] Current config (no change)...")
ref, sw, act = test_speed_ref()
print(f"  Ref reg reads: {ref}, SW=0x{sw:04X}, Actual P01.07-09={act}")

# Try different values for reg 2102
# ABB typical values: 2=AI2, 3=Keypad, 7=Fieldbus, 8=EFB, 19=Comm
for test_val in [2, 3, 7, 8, 19, 0]:
    print(f"\n[TEST] Setting reg 2102 = {test_val}...")
    try:
        r = client.write_register(address=2102, value=test_val, device_id=1)
        if r.isError():
            print(f"  Write failed: {r}")
            continue
    except Exception as e:
        print(f"  Write error: {e}")
        continue
    
    time.sleep(0.3)
    # Verify it was written
    verify = client.read_holding_registers(address=2102, count=1, device_id=1)
    actual_val = verify.registers[0]
    print(f"  Read back: {actual_val}")
    
    if actual_val != test_val:
        print(f"  Value didn't stick (wrote {test_val}, got {actual_val})")
        continue
    
    ref, sw, act = test_speed_ref()
    print(f"  Ref reg reads: {ref}, SW=0x{sw:04X}, Actual P01.07-09={act}")
    
    if ref == 4000 or ref > 0:
        print(f"\n  >>> SUCCESS! Value {test_val} makes fieldbus ref work! <<<")
        print(f"  Leaving reg 2102 = {test_val}")
        client.close()
        exit(0)

# If nothing worked, restore original
print(f"\n[RESTORE] Setting reg 2102 back to {orig_2102}")
client.write_register(address=2102, value=orig_2102, device_id=1)

# Let's also try changing P22.11 area and other ref chain params
print("\n\n=== Trying P22 Freq Ref Chain ===")
for addr, name in [(2210, "P22.10"), (2211, "P22.11"), (2200, "P22.00")]:
    res = client.read_holding_registers(address=addr, count=1, device_id=1)
    if hasattr(res, 'registers'):
        print(f"  {name} (reg {addr}) = {res.registers[0]}")

client.close()
print("\nDone.")
