"""Quick motor test - Start at 20%, monitor 10s, then stop."""
from pymodbus.client import ModbusSerialClient
import config, time

client = ModbusSerialClient(
    port=config.COM_PORT,
    baudrate=config.BAUD_RATE,
    parity=config.PARITY,
    stopbits=config.STOP_BITS,
    bytesize=config.BYTE_SIZE,
    timeout=2.0,
)

if not client.connect():
    print("ERROR: Cannot open COM port!")
    exit(1)
print("[OK] Connected")

# Set speed to 10%
speed_raw = int(10.0 * config.SPEED_REF_SCALE / 100.0)
print(f"[CMD] Setting speed to 10% (raw={speed_raw})...")
client.write_register(address=config.REG_SPEED_REF, value=speed_raw, device_id=config.SLAVE_ID)
time.sleep(0.2)

# STOP -> RUN transition
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_STOP, device_id=config.SLAVE_ID)
time.sleep(0.3)
print("[CMD] START at 10%!")
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_RUN, device_id=config.SLAVE_ID)

print("\n--- Monitoring (10 seconds) ---")
for i in range(10):
    time.sleep(1)
    res = client.read_holding_registers(address=config.REG_STATUS_WORD, count=3, device_id=config.SLAVE_ID)
    if hasattr(res, "registers"):
        sw = res.registers[0]
        spd = res.registers[1] * 100.0 / config.SPEED_REF_SCALE
        cur = res.registers[2] * 0.1
        running = bool(sw & config.SW_RUNNING)
        fault = bool(sw & config.SW_FAULT)
        print(f"  [{i+1:2d}s] SW=0x{sw:04X} | Running={running} | Fault={fault} | Speed={spd:.1f}% | Current={cur:.2f}A")

print("\n[CMD] STOP...")
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_STOP, device_id=config.SLAVE_ID)
time.sleep(2)

res = client.read_holding_registers(address=config.REG_STATUS_WORD, count=3, device_id=config.SLAVE_ID)
if hasattr(res, "registers"):
    sw = res.registers[0]
    print(f"[Final] SW=0x{sw:04X} | Running={bool(sw & config.SW_RUNNING)}")

client.close()
print("[OK] Done.")
