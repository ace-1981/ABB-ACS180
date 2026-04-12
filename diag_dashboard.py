"""Diagnose: test FC06 vs FC16 and verify motor starts."""
from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(
    port="COM4", baudrate=19200, parity="E", stopbits=1, bytesize=8, timeout=2.0
)
if not client.connect():
    print("ERROR: Cannot open COM4!")
    exit(1)

def signed(v):
    return v if v < 0x8000 else v - 0x10000

def read_all():
    r = client.read_holding_registers(address=0, count=6, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) >= 6:
        cw, ref1, ref2, sw, act1, act2 = r.registers
        print(f"  CW=0x{cw:04X} Ref1={ref1} SW=0x{sw:04X} Act1={signed(act1)} Act2={signed(act2)}")
        return sw
    else:
        print(f"  READ ERROR: {r}")
        return None

# Stop first
print("=== STOP ===")
r = client.write_register(address=0, value=0x047E, device_id=1)
print(f"  FC06 stop: error={r.isError()}")
time.sleep(1)
read_all()

# Test 1: FC16 (write_registers) - what dashboard uses
print("\n=== TEST 1: FC16 write_registers [CW=0x047F, Ref=10000] ===")
r = client.write_registers(address=0, values=[0x047F, 10000], device_id=1)
print(f"  FC16 result: error={r.isError()}, resp={r}")
time.sleep(2)
sw = read_all()
if sw and (sw & 0x0004):
    print("  >>> MOTOR RUNNING! FC16 works!")
else:
    print("  >>> Motor NOT running with FC16!")

# Stop
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)

# Test 2: FC06 separate writes - what fix_freq_ref.py used
print("\n=== TEST 2: FC06 separate writes ===")
r1 = client.write_register(address=1, value=10000, device_id=1)
print(f"  FC06 ref=10000: error={r1.isError()}")
time.sleep(0.1)
r2 = client.write_register(address=0, value=0x047F, device_id=1)
print(f"  FC06 CW=0x047F: error={r2.isError()}")
time.sleep(2)
sw = read_all()
if sw and (sw & 0x0004):
    print("  >>> MOTOR RUNNING! FC06 works!")
else:
    print("  >>> Motor NOT running with FC06!")

# Test 3: Try different CW sequence
print("\n=== TEST 3: State machine sequence ===")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(1)
# Write ref first
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
# CW sequence: OFF -> READY -> RUN
for cw, label in [(0x0406, "Shutdown"), (0x0407, "SwitchOn"), (0x047F, "Run+EXT2")]:
    r = client.write_register(address=0, value=cw, device_id=1)
    time.sleep(0.3)
    print(f"  {label} (0x{cw:04X}): error={r.isError()}")
    read_all()

time.sleep(2)
print("\n=== Final status ===")
sw = read_all()
if sw and (sw & 0x0004):
    print(">>> MOTOR RUNNING!")
else:
    print(">>> Motor NOT running")
    # Read more params
    for g, i, name in [(1,7,"OutFreq"), (1,8,"Current"), (1,1,"MotorSpeed"), (3,9,"EFB1")]:
        a = g * 100 + i - 1
        r = client.read_holding_registers(address=a, count=1, device_id=1)
        if hasattr(r, 'registers'):
            print(f"  P{g:02d}.{i:02d} ({name}) = {signed(r.registers[0])}")

# Always stop at end
print("\n=== Stopping ===")
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(1)
read_all()
client.close()
print("Done.")
