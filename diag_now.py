"""Quick diagnostic: try to start motor and monitor status."""
from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(port="COM4", baudrate=19200, parity="E", stopbits=1, bytesize=8, timeout=2)
if not client.connect():
    print("ERROR: Cannot open COM4")
    exit()
print("[OK] Connected")

def read_status():
    regs = client.read_holding_registers(address=0, count=6, device_id=1)
    if not hasattr(regs, "registers"):
        print("  ERROR reading registers")
        return None
    r = regs.registers
    sw = r[3]
    print(f"  CW=0x{r[0]:04X}  Ref1={r[1]}  SW=0x{sw:04X}  Act1={r[4]}  Act2={r[5]}")
    print(f"  Ready={bool(sw&1)}  ReadyRun={bool(sw&2)}  Running={bool(sw&4)}  "
          f"Fault={bool(sw&8)}  OFF2={bool(sw&0x10)}  OFF3={bool(sw&0x20)}")
    return sw

# Step 1: Send STOP (clean state)
print("\n[1] Sending STOP (0x047E, ref=0)...")
r = client.write_registers(address=0, values=[0x047E, 0], device_id=1)
print(f"  Write OK: {not r.isError()}")
time.sleep(0.3)
read_status()

# Step 2: Send RUN with 50% speed
ref = 10000
cw_run = 0x047F
print(f"\n[2] Sending RUN (CW=0x{cw_run:04X}, Ref={ref})...")
r = client.write_registers(address=0, values=[cw_run, ref], device_id=1)
print(f"  Write OK: {not r.isError()}")
time.sleep(1)
print("\n[3] Status after 1 sec:")
read_status()

time.sleep(2)
print("\n[4] Status after 3 sec:")
sw = read_status()

if sw is not None and not (sw & 0x0004):
    print("\n*** Motor NOT running. Checking possible issues... ***")
    # Check if EFB comm timeout issue - P30.01
    for g, i, desc in [(30, 1, "EFB comm fault action"), (30, 2, "EFB comm timeout"),
                        (58, 1, "Fieldbus type"), (58, 6, "FB ctrl profile")]:
        addr = g * 100 + i - 1
        r2 = client.read_holding_registers(address=addr, count=1, device_id=1)
        val = r2.registers[0] if hasattr(r2, "registers") and len(r2.registers) > 0 else "ERR"
        print(f"  P{g:02d}.{i:02d} = {val}  ({desc})")

# Stop motor before exit
print("\n[5] Sending STOP...")
client.write_registers(address=0, values=[0x047E, 0], device_id=1)

client.close()
print("\nDone.")
