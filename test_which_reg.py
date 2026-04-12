"""Test: Which register is the actual speed reference? Reg 1 or Reg 2?"""
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

print("=== Which Register Controls Speed? ===\n")

# Read initial state
r = client.read_holding_registers(address=0, count=10, device_id=1)
if hasattr(r, 'registers'):
    print(f"Initial: CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}")
    for i in range(4, min(10, len(r.registers))):
        if r.registers[i] != 0:
            print(f"  REG[{i}] = {r.registers[i]}")

# Start motor with known references
print("\n--- Test 1: REG1=10000, REG2=4000 (current) ---")
client.write_register(address=1, value=10000, device_id=1)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
time.sleep(5)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}  REG4={r.registers[4]}  REG5={r.registers[5]}")

# Test 2: Change REG2 to 20000 (100%), keep REG1 at 10000
print("\n--- Test 2: REG1=10000, REG2=20000 ---")
print("    (if voltage INCREASES, REG2 is the real reference!)")
client.write_register(address=2, value=20000, device_id=1)  
time.sleep(5)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}  REG4={r.registers[4]}  REG5={r.registers[5]}")
input(">>> Check motor voltage/sound now. Press Enter for next test...")

# Test 3: REG2 to 0, keep REG1 at 10000
print("\n--- Test 3: REG1=10000, REG2=0 ---")
print("    (if voltage DROPS, REG2 is the real reference!)")
client.write_register(address=2, value=0, device_id=1)
time.sleep(5)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}  REG4={r.registers[4]}  REG5={r.registers[5]}")
input(">>> Check motor voltage/sound now. Press Enter for next test...")

# Test 4: Change REG1 to 20000, keep REG2 at 0
print("\n--- Test 4: REG1=20000, REG2=0 ---")
print("    (if voltage INCREASES, REG1 is the real reference!)")
client.write_register(address=1, value=20000, device_id=1)
time.sleep(5)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}  REG4={r.registers[4]}  REG5={r.registers[5]}")
input(">>> Check motor voltage/sound now. Press Enter for next test...")

# Test 5: Both at 20000
print("\n--- Test 5: REG1=20000, REG2=20000 ---")
client.write_register(address=1, value=20000, device_id=1)
client.write_register(address=2, value=20000, device_id=1)
time.sleep(5)
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    print(f"  CW=0x{r.registers[0]:04X}  REG1={r.registers[1]}  REG2={r.registers[2]}  SW=0x{r.registers[3]:04X}  REG4={r.registers[4]}  REG5={r.registers[5]}")
input(">>> Check motor voltage/sound now. Press Enter to stop...")

# Stop
client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
