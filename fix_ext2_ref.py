"""Fix EXT2 reference source - P21.03 must be Fieldbus (2)."""
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

# Read current P21.02 and P21.03
res = client.read_holding_registers(address=2102, count=2, device_id=1)
if hasattr(res, 'registers'):
    print(f"BEFORE: P21.02 (EXT1 ref) = {res.registers[0]}, P21.03 (EXT2 ref) = {res.registers[1]}")

# Change P21.03 to 2 (Fieldbus)
print("\nWriting P21.03 = 2 (Fieldbus)...")
wr = client.write_register(address=2103, value=2, device_id=1)
print(f"  Write result: error={wr.isError() if hasattr(wr, 'isError') else 'unknown'}")

# Verify
time.sleep(0.3)
res = client.read_holding_registers(address=2102, count=2, device_id=1)
if hasattr(res, 'registers'):
    print(f"AFTER:  P21.02 (EXT1 ref) = {res.registers[0]}, P21.03 (EXT2 ref) = {res.registers[1]}")

# Now test: stop, set speed, start, monitor
print("\n--- Motor Test ---")
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

# Set speed to 50% (25Hz)
speed_ref = 10000
client.write_register(address=1, value=speed_ref, device_id=1)
time.sleep(0.2)

# Start
client.write_register(address=0, value=config.CW_RUN, device_id=1)
print(f"Motor started with ref={speed_ref} (50%)")

# Monitor for 15 seconds
for i in range(15):
    time.sleep(1)
    r0 = client.read_holding_registers(address=0, count=6, device_id=1)
    sw = r0.registers[3] if hasattr(r0, 'registers') else 0
    running = bool(sw & 0x0004) if sw else False
    ref_back = r0.registers[1] if hasattr(r0, 'registers') else 0
    
    # Read P01 for actual freq/current
    p1 = client.read_holding_registers(address=101, count=19, device_id=1)
    p1v = {}
    if hasattr(p1, 'registers'):
        for j, v in enumerate(p1.registers):
            sv = v if v < 32768 else v - 65536
            if sv != 0:
                p1v[f"P01.{j+1:02d}"] = sv
    
    print(f"  t={i+1:2d}s: SW=0x{sw:04X} Running={running} Ref={ref_back} | P01 non-zero: {p1v}")

# Try different speeds
print("\n--- Speed Ramp Test ---")
for pct in [10, 30, 50, 80, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(3)
    r0 = client.read_holding_registers(address=0, count=6, device_id=1)
    ref_back = r0.registers[1] if hasattr(r0, 'registers') else 0
    p1 = client.read_holding_registers(address=101, count=19, device_id=1)
    p1v = {}
    if hasattr(p1, 'registers'):
        for j, v in enumerate(p1.registers):
            sv = v if v < 32768 else v - 65536
            if sv != 0:
                p1v[f"P01.{j+1:02d}"] = sv
    print(f"  {pct:3d}% (ref={val:5d}) -> reads {ref_back:5d} | P01: {p1v}")

# Stop
client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
