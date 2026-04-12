"""Test motor after fieldbus configuration."""
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

def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

# Verify settings
print("=== Fieldbus Config Verification ===")
print(f"  P22.11 (Ext1 speed ref1) = {read_param(22,11)}  (should be 8=EFB ref1)")
print(f"  P28.11 (Ext1 freq ref1)  = {read_param(28,11)}  (should be 8=EFB ref1)")
print(f"  P22.18 (Ext2 speed ref1) = {read_param(22,18)}  (should be 8=EFB ref1)")
print(f"  P03.09 (EFB reference 1) = {signed(read_param(3,9))}")

# Stop first
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

# Set 50% speed reference
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.2)

# Start
client.write_register(address=0, value=config.CW_RUN, device_id=1)
print("\nMotor started with ref=10000 (50%)")
print("Check: Is the motor spinning now? Does the sound change?\n")

# Monitor for 20 seconds
for i in range(20):
    time.sleep(1)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        ref = r.registers[1]
        sw = r.registers[3]
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        running = bool(sw & 0x0004)
        
        efb1 = signed(read_param(3, 9))
        
        # Read some actual signal params
        p0107 = signed(read_param(1, 7))  # might be output freq
        p0108 = signed(read_param(1, 8))  # might be output current
        p0101 = signed(read_param(1, 1))  # motor speed
        
        print(f"  t={i+1:2d}s: Ref={ref} SW=0x{sw:04X} Run={running} Act1={act1} Act2={act2} EFB1={efb1} P01.01={p0101} P01.07={p0107} P01.08={p0108}")

# Speed ramp test
print("\n=== Speed Ramp ===")
for pct in [10, 25, 50, 75, 100]:
    val = int(pct / 100.0 * 20000)
    client.write_register(address=1, value=val, device_id=1)
    time.sleep(4)
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        act1 = signed(r.registers[4])
        act2 = signed(r.registers[5])
        efb1 = signed(read_param(3, 9))
        p0101 = signed(read_param(1, 1))
        print(f"  {pct:3d}% (ref={val:5d}): Act1={act1} Act2={act2} EFB1={efb1} P01.01={p0101}")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
