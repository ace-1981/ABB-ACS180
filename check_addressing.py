"""Try both Mode 0 and Mode 1 addressing to find the correct parameter mapping."""
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

# Stop motor
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(0.5)

def read_reg(addr):
    try:
        res = client.read_holding_registers(address=addr, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except:
        pass
    return None

print("=== Determining Addressing Mode ===\n")

# Try to read P58.33 in BOTH modes
# Mode 0: addr = 100*58 + 33 = 5833
# Mode 1: addr = 256*58 + 33 = 14881
v_m0 = read_reg(5833)
v_m1 = read_reg(14881)
print(f"P58.33 at Mode 0 addr (5833): {v_m0}")
print(f"P58.33 at Mode 1 addr (14881): {v_m1}")

# Try P22.11 in both modes
v_m0 = read_reg(2211)
v_m1 = read_reg(256*22 + 11)  # 5643
print(f"\nP22.11 at Mode 0 addr (2211): {v_m0}")
print(f"P22.11 at Mode 1 addr (5643): {v_m1}")

# Try P20.01 in both modes
v_m0 = read_reg(2001)
v_m1 = read_reg(256*20 + 1)  # 5121
print(f"\nP20.01 at Mode 0 addr (2001): {v_m0}")
print(f"P20.01 at Mode 1 addr (5121): {v_m1}")

# Read P58.101-P58.106 in BOTH modes
print("\n=== P58.101-P58.106 (Data I/O) ===")
for idx in range(101, 115):
    addr_m0 = 100 * 58 + idx  # 5801 + idx
    addr_m1 = 256 * 58 + idx  # 14848 + idx
    v_m0 = read_reg(addr_m0)
    v_m1 = read_reg(addr_m1)
    print(f"  P58.{idx} (I/O {idx-100}): Mode0={v_m0}  Mode1={v_m1}")

# Read P03.09 in both modes
addr_m0 = 100*3 + 9
addr_m1 = 256*3 + 9
v_m0 = read_reg(addr_m0)
v_m1 = read_reg(addr_m1)
print(f"\nP03.09 (EFB Ref1): Mode0={v_m0}  Mode1={v_m1}")

# Try to read P22.11 to see our setting
print("\n=== Verify our P22.11 setting ===")
for addr in [2211, 5643]:
    v = read_reg(addr)
    print(f"  P22.11 at addr {addr}: {v}")

# Also read first 14 registers (Data I/O)
print("\n=== First 14 Modbus registers ===")
for addr in range(0, 14):
    v = read_reg(addr)
    sv = v if v is None or v < 32768 else v - 65536
    print(f"  Reg {addr}: {v} ({sv})")

client.close()
