"""Deep diagnosis - check reference path and try different approaches."""
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

print("=== DEEP REFERENCE DIAGNOSIS ===\n")

# Re-read addresses 2000-2220 directly
print("--- Re-reading registers 2000-2230 ---")
for start in range(2000, 2230, 10):
    try:
        res = client.read_holding_registers(address=start, count=10, device_id=1)
        if hasattr(res, 'registers'):
            for i, val in enumerate(res.registers):
                if val != 0:
                    addr = start + i
                    print(f"  Reg {addr} = {val} (0x{val:04X})")
    except:
        pass

# Check what's in reg 1 (speed ref) right now - motor stopped
print("\n--- Current Fieldbus Registers (stopped) ---")
res = client.read_holding_registers(address=0, count=6, device_id=1)
print(f"  Regs 0-5: {res.registers}")

# Start motor and check
print("\n--- Starting motor ---")
client.write_register(address=1, value=4000, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(0.3)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
time.sleep(1)

res = client.read_holding_registers(address=0, count=6, device_id=1)
print(f"  After start - Regs 0-5: {res.registers}")
print(f"  We wrote 4000 to reg 1, but it reads: {res.registers[1]}")

# The value 17400 suggests something else controls the ref.
# Let's check: what does the drive THINK its reference source is?
# Try writing to different possible reference registers
print("\n--- Trying alternative reference registers ---")

# Some ABB drives use register 2 for the reference
client.write_register(address=2, value=4000, device_id=1)
time.sleep(0.5)
res = client.read_holding_registers(address=0, count=6, device_id=1)
print(f"  After write to reg 2: {res.registers}")

# Check P01 actual values (operating data / feedback)
print("\n--- P01 Operating Data ---")
for p in range(1, 20):
    try:
        res = client.read_holding_registers(address=100+p, count=1, device_id=1)
        if hasattr(res, 'registers'):
            print(f"  P01.{p:02d} = {res.registers[0]} (0x{res.registers[0]:04X})")
    except:
        pass

# Try P01.01 - might be actual output frequency
print("\n--- Checking actual output frequency ---")
# Read P01.01 through P01.09 - these are typically actual values
for p in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
    try:
        res = client.read_holding_registers(address=100+p, count=1, device_id=1)
        if hasattr(res, 'registers'):
            val = res.registers[0]
            if val > 32767:
                val = val - 65536
            print(f"  P01.{p:02d} = {val}")
    except:
        pass

# Stop
print("\n[STOP]")
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

# Read P01 again when stopped
print("\n--- P01 after stop ---")
for p in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
    try:
        res = client.read_holding_registers(address=100+p, count=1, device_id=1)
        if hasattr(res, 'registers'):
            val = res.registers[0]
            if val > 32767:
                val = val - 65536
            print(f"  P01.{p:02d} = {val}")
    except:
        pass

client.close()
print("\nDone.")
