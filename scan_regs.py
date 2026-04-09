"""Scan registers while motor is running to find actual speed/freq/current."""
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

# Start motor at 20%
speed_raw = int(20.0 * config.SPEED_REF_SCALE / 100.0)
client.write_register(address=config.REG_SPEED_REF, value=speed_raw, device_id=config.SLAVE_ID)
time.sleep(0.2)
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_STOP, device_id=config.SLAVE_ID)
time.sleep(0.3)
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_RUN, device_id=config.SLAVE_ID)
print("[OK] Motor started at 20%. Waiting 3s to stabilize...")
time.sleep(3)

# Scan holding registers in blocks
print("\n=== SCANNING HOLDING REGISTERS (0-99) ===")
for start in range(0, 100, 10):
    try:
        res = client.read_holding_registers(address=start, count=10, device_id=config.SLAVE_ID)
        if hasattr(res, "registers"):
            for i, val in enumerate(res.registers):
                if val != 0:
                    addr = start + i
                    print(f"  Reg {addr:4d} (0x{addr:04X}) = {val:6d}  (0x{val:04X})")
    except Exception as e:
        pass

# Scan input registers too
print("\n=== SCANNING INPUT REGISTERS (0-99) ===")
for start in range(0, 100, 10):
    try:
        res = client.read_input_registers(address=start, count=10, device_id=config.SLAVE_ID)
        if hasattr(res, "registers"):
            for i, val in enumerate(res.registers):
                if val != 0:
                    addr = start + i
                    print(f"  Reg {addr:4d} (0x{addr:04X}) = {val:6d}  (0x{val:04X})")
    except Exception as e:
        pass

# Wide scan holding registers 100-10000
print("\n=== SCANNING HOLDING REGISTERS (100-10000) ===")
for start in range(100, 10000, 10):
    try:
        res = client.read_holding_registers(address=start, count=10, device_id=config.SLAVE_ID)
        if hasattr(res, "registers"):
            for i, val in enumerate(res.registers):
                if val != 0:
                    addr = start + i
                    print(f"  HReg {addr:5d} (0x{addr:04X}) = {val:6d}  (0x{val:04X})")
    except Exception:
        pass

# Wide scan input registers 100-10000
print("\n=== SCANNING INPUT REGISTERS (100-10000) ===")
for start in range(100, 10000, 10):
    try:
        res = client.read_input_registers(address=start, count=10, device_id=config.SLAVE_ID)
        if hasattr(res, "registers"):
            for i, val in enumerate(res.registers):
                if val != 0:
                    addr = start + i
                    print(f"  IReg {addr:5d} (0x{addr:04X}) = {val:6d}  (0x{val:04X})")
    except Exception:
        pass

# Stop motor
print("\n[CMD] STOP...")
client.write_register(address=config.REG_CONTROL_WORD, value=config.CW_STOP, device_id=config.SLAVE_ID)
client.close()
print("[OK] Done.")
