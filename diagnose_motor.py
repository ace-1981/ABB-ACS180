"""Diagnose why motor gets voltage but doesn't spin."""
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

print("=== ACS180 Motor Diagnosis ===\n")

# 1. Read status
res = client.read_holding_registers(address=3, count=1, device_id=1)
sw = res.registers[0]
print(f"Status Word: 0x{sw:04X}")
print(f"  Bit 0  Ready to switch on: {bool(sw & 0x0001)}")
print(f"  Bit 1  Switched on:        {bool(sw & 0x0002)}")
print(f"  Bit 2  Operation enabled:   {bool(sw & 0x0004)}")
print(f"  Bit 3  Fault:               {bool(sw & 0x0008)}")
print(f"  Bit 4  Voltage enabled:     {bool(sw & 0x0010)}")
print(f"  Bit 5  Quick stop:          {bool(sw & 0x0020)}")
print(f"  Bit 6  Switch on disabled:  {bool(sw & 0x0040)}")
print(f"  Bit 7  Warning:             {bool(sw & 0x0080)}")
print(f"  Bit 9  Remote:              {bool(sw & 0x0200)}")
print(f"  Bit 12 Ext ctrl:            {bool(sw & 0x1000)}")

if sw & 0x0008:
    print("\n*** FAULT DETECTED - resetting... ***")
    client.write_register(address=0, value=config.CW_FAULT_RESET, device_id=1)
    time.sleep(0.5)
    client.write_register(address=0, value=config.CW_STOP, device_id=1)
    time.sleep(0.3)
    res = client.read_holding_registers(address=3, count=1, device_id=1)
    sw = res.registers[0]
    print(f"After reset: 0x{sw:04X} Fault={bool(sw & 0x0008)}")

# 2. Proper DS402 state machine sequence
print("\n--- DS402 State Machine Sequence ---")

# Step 1: Shutdown (ready to switch on)
# CW = 0x0006 = bits 1,2 ON (voltage, quick stop), bit 0 OFF
print("[1] Shutdown -> Ready to switch on (CW=0x0006)...")
client.write_register(address=0, value=0x0006, device_id=1)
time.sleep(0.5)
res = client.read_holding_registers(address=3, count=1, device_id=1)
print(f"    SW=0x{res.registers[0]:04X}")

# Step 2: Switch on
# CW = 0x0007 = bits 0,1,2 ON
print("[2] Switch on (CW=0x0007)...")
client.write_register(address=0, value=0x0007, device_id=1)
time.sleep(0.5)
res = client.read_holding_registers(address=3, count=1, device_id=1)
print(f"    SW=0x{res.registers[0]:04X}")

# Step 3: Set speed reference BEFORE enable operation
print("[3] Setting speed to 20% (raw=4000)...")
client.write_register(address=1, value=4000, device_id=1)
time.sleep(0.2)

# Step 4: Enable operation
# CW = 0x000F = bits 0,1,2,3 ON
print("[4] Enable operation (CW=0x000F)...")
client.write_register(address=0, value=0x000F, device_id=1)
time.sleep(0.5)
res = client.read_holding_registers(address=3, count=1, device_id=1)
sw = res.registers[0]
print(f"    SW=0x{sw:04X} Running={bool(sw & 0x0004)}")

# Also try with ABB extended bits (bit 4=ramp, bit 5=unfreeze ramp, bit 6=unfreeze ref, bit 10=PLC)
print("[4b] Enable with ABB bits (CW=0x047F)...")
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(0.5)
res = client.read_holding_registers(address=3, count=1, device_id=1)
sw = res.registers[0]
print(f"    SW=0x{sw:04X} Running={bool(sw & 0x0004)}")

# Monitor for 10 seconds
print("\n--- Monitoring (10s) ---")
for i in range(10):
    time.sleep(1)
    res = client.read_holding_registers(address=0, count=6, device_id=1)
    cw = res.registers[0]
    sref = res.registers[1]
    sw = res.registers[3] if len(res.registers) > 3 else 0
    print(f"  [{i+1:2d}s] CW=0x{cw:04X} SpeedRef={sref} SW=0x{sw:04X} Running={bool(sw & 0x0004)}")

# Stop
print("\n[STOP]")
client.write_register(address=0, value=0x0006, device_id=1)
client.close()
print("Done.")
