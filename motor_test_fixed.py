"""Motor run test with reg 2102=2, monitor actual output."""
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

print("=== Motor Test with Fixed Reference ===\n")

# Ensure reg 2102 = 2 (fieldbus ref)
client.write_register(address=2102, value=2, device_id=1)
time.sleep(0.2)

# Set speed to 50% (10000/20000 = 25Hz)
speed_raw = 10000
print(f"Setting speed to 50% (raw={speed_raw}, ~25Hz)...")
client.write_register(address=1, value=speed_raw, device_id=1)
time.sleep(0.2)

# Start
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(0.3)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
print("Motor STARTED!\n")

print("--- Monitoring 15 seconds ---")
print(f"{'Sec':>3s} | {'SW':>6s} | {'Running':>7s} | {'Ref(reg1)':>9s} | {'P01.07':>6s} | {'P01.08':>6s} | {'P01.09':>6s} | {'P01.10':>7s}")
print("-" * 75)

for i in range(15):
    time.sleep(1)
    r0 = client.read_holding_registers(address=0, count=6, device_id=1)
    sw = r0.registers[3]
    ref = r0.registers[1]
    
    p1 = client.read_holding_registers(address=107, count=4, device_id=1)
    vals = p1.registers if hasattr(p1, 'registers') else [0]*4
    # Convert to signed
    vals_s = [v if v < 32768 else v - 65536 for v in vals]
    
    running = bool(sw & 0x0004)
    print(f"{i+1:3d} | 0x{sw:04X} | {'YES' if running else 'NO':>7s} | {ref:>9d} | {vals_s[0]:>6d} | {vals_s[1]:>6d} | {vals_s[2]:>6d} | {vals_s[3]:>7d}")

# Now change speed to 80% and monitor
print(f"\n--- Changing to 80% (raw=16000) ---")
client.write_register(address=1, value=16000, device_id=1)
for i in range(8):
    time.sleep(1)
    r0 = client.read_holding_registers(address=0, count=6, device_id=1)
    sw = r0.registers[3]
    ref = r0.registers[1]
    p1 = client.read_holding_registers(address=107, count=4, device_id=1)
    vals = p1.registers if hasattr(p1, 'registers') else [0]*4
    vals_s = [v if v < 32768 else v - 65536 for v in vals]
    running = bool(sw & 0x0004)
    print(f"{i+16:3d} | 0x{sw:04X} | {'YES' if running else 'NO':>7s} | {ref:>9d} | {vals_s[0]:>6d} | {vals_s[1]:>6d} | {vals_s[2]:>6d} | {vals_s[3]:>7d}")

# Stop
print("\n[STOP]")
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(3)

r0 = client.read_holding_registers(address=0, count=6, device_id=1)
sw = r0.registers[3]
p1 = client.read_holding_registers(address=107, count=4, device_id=1)
vals = p1.registers if hasattr(p1, 'registers') else [0]*4
vals_s = [v if v < 32768 else v - 65536 for v in vals]
print(f"End | 0x{sw:04X} | {'YES' if bool(sw & 0x0004) else 'NO':>7s} | {0:>9d} | {vals_s[0]:>6d} | {vals_s[1]:>6d} | {vals_s[2]:>6d} | {vals_s[3]:>7d}")

client.close()
print("\nDone. Motor should have ramped up and down.")
