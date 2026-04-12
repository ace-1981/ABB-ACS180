"""Try ALL possible values for P21.02 (reg 2102) to find Fieldbus."""
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

def run_and_check(label, speed_raw=10000):
    """Start motor, write ref, wait, read back actual values."""
    client.write_register(address=1, value=speed_raw, device_id=1)
    time.sleep(0.1)
    client.write_register(address=0, value=config.CW_STOP, device_id=1)
    time.sleep(0.3)
    client.write_register(address=0, value=config.CW_RUN, device_id=1)
    time.sleep(3)  # Wait 3s for ramp

    results = []
    for _ in range(3):
        time.sleep(1)
        r0 = client.read_holding_registers(address=0, count=6, device_id=1)
        ref = r0.registers[1]
        sw = r0.registers[3]

        p1 = client.read_holding_registers(address=101, count=10, device_id=1)
        vals = []
        if hasattr(p1, 'registers'):
            vals = [v if v < 32768 else v - 65536 for v in p1.registers]
        results.append((ref, sw, vals))

    client.write_register(address=0, value=config.CW_STOP, device_id=1)
    time.sleep(2)
    return results

print("=== Finding Fieldbus Reference Source ===")
print("Testing all possible P21.02 values (0-20)...\n")

# Save original
orig = client.read_holding_registers(address=2102, count=1, device_id=1).registers[0]
print(f"Original P21.02 = {orig}\n")

# First, read ALL P01 parameter names while motor is stopped
print("P01 values (motor stopped):")
p1_stop = client.read_holding_registers(address=101, count=19, device_id=1)
if hasattr(p1_stop, 'registers'):
    for i, v in enumerate(p1_stop.registers):
        sv = v if v < 32768 else v - 65536
        if sv != 0:
            print(f"  P01.{i+1:02d} = {sv}")

print()

for test_val in range(0, 21):
    # Try to write
    try:
        r = client.write_register(address=2102, value=test_val, device_id=1)
        if r.isError():
            continue
    except:
        continue

    # Read back to verify
    time.sleep(0.2)
    actual = client.read_holding_registers(address=2102, count=1, device_id=1).registers[0]
    if actual != test_val:
        continue  # Value not accepted

    # This value was accepted, test it
    results = run_and_check(f"P21.02={test_val}")
    last_ref, last_sw, last_p1 = results[-1]
    running = bool(last_sw & 0x0004)

    # Key indicators: ref should be 10000, and P01 values should show actual output freq
    p7 = last_p1[6] if len(last_p1) > 6 else 0
    p8 = last_p1[7] if len(last_p1) > 7 else 0
    p9 = last_p1[8] if len(last_p1) > 8 else 0

    print(f"  P21.02={test_val:2d} => Ref={last_ref:6d} SW=0x{last_sw:04X} Run={running} P01.07={p7} P01.08={p8} P01.09={p9}")

# Restore
print(f"\nRestoring P21.02 = {orig}")
client.write_register(address=2102, value=orig, device_id=1)

client.close()
print("Done.")
