"""Switch to Mode 1 to read P58.101-P58.114 Data I/O mapping.
Correct address formula: PDU_addr = 100*group + index - 1 (Mode 0)
                         PDU_addr = 256*group + index - 1 (Mode 1)
"""
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

def read_reg(addr):
    try:
        res = client.read_holding_registers(address=addr, count=1, device_id=1)
        if hasattr(res, 'registers') and len(res.registers) > 0:
            return res.registers[0]
    except:
        pass
    return None

def write_reg(addr, value):
    try:
        res = client.write_register(address=addr, value=value, device_id=1)
        return not res.isError() if hasattr(res, 'isError') else False
    except:
        return False

def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

# Mode 0 addr formula: group*100 + index - 1
def m0_addr(group, index):
    return group * 100 + index - 1

# Mode 1 addr formula: group*256 + index - 1
def m1_addr(group, index):
    return group * 256 + index - 1

# Stop motor
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

# Verify current Mode 0 addressing
print("=== Current state (Mode 0) ===")
print(f"  P58.33 (Addressing mode) at addr {m0_addr(58,33)} = {read_reg(m0_addr(58,33))}")
print(f"  P58.01 (Protocol enable) at addr {m0_addr(58,1)} = {read_reg(m0_addr(58,1))}")
print(f"  P58.03 (Node address) at addr {m0_addr(58,3)} = {read_reg(m0_addr(58,3))}")

# Switch to Mode 1
print("\n=== Switching to Mode 1 ===")
p58_33_m0 = m0_addr(58, 33)  # 5832
print(f"  Writing P58.33 = 1 at addr {p58_33_m0}...")
ok = write_reg(p58_33_m0, 1)
print(f"  Result: {'OK' if ok else 'FAILED'}")
time.sleep(1)

# In Mode 1 now - verify by reading P58.33 at Mode 1 address
p58_33_m1 = m1_addr(58, 33)  # 14880
print(f"  Verify P58.33 at Mode 1 addr {p58_33_m1} = {read_reg(p58_33_m1)}")

# Also try reading P58.01 at Mode 1 addr to confirm mode switch
p58_01_m1 = m1_addr(58, 1)  # 14847
print(f"  P58.01 at Mode 1 addr {p58_01_m1} = {read_reg(p58_01_m1)}")

# Read P58.101-P58.114 (Data I/O mapping) at Mode 1 addresses
print("\n=== P58.101-P58.114 (Data I/O Mapping) ===")
io_names = {1: "CW 16bit", 2: "Ref1 16bit", 3: "Ref2 16bit", 
            4: "SW 16bit", 5: "Act1 16bit", 6: "Act2 16bit",
            0: "None", 11: "CW 32bit", 12: "Ref1 32bit", 
            13: "Ref2 32bit", 14: "SW 32bit", 15: "Act1 32bit", 16: "Act2 32bit",
            31: "RO/DIO CW", 32: "AO1 data", 40: "Feedback data", 41: "Setpoint data"}
for idx in range(101, 115):
    addr = m1_addr(58, idx)
    v = read_reg(addr)
    name = io_names.get(v, f"Unknown({v})") if v is not None else "N/A"
    reg_num = idx - 101  # Register 0-13
    print(f"  P58.{idx} (Data I/O {idx-100} -> Reg[{reg_num}]) at addr {addr} = {v} ({name})")

# Also read P22.11 at Mode 1 to verify
p22_11_m1 = m1_addr(22, 11)
print(f"\n  P22.11 at Mode 1 addr {p22_11_m1} = {read_reg(p22_11_m1)}")

# And P20.01
p20_01_m1 = m1_addr(20, 1)
print(f"  P20.01 at Mode 1 addr {p20_01_m1} = {read_reg(p20_01_m1)}")

# Read P03.09 at Mode 1
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.3)
p03_09_m1 = m1_addr(3, 9)
p03_10_m1 = m1_addr(3, 10)
print(f"\n  Wrote 10000 to reg 1")
print(f"  P03.09 at Mode 1 addr {p03_09_m1} = {signed(read_reg(p03_09_m1))}")
print(f"  P03.10 at Mode 1 addr {p03_10_m1} = {signed(read_reg(p03_10_m1))}")

# Read P58.26 (EFB ref1 type)
p58_26_m1 = m1_addr(58, 26)
print(f"\n  P58.26 (EFB ref1 type) at Mode 1 addr {p58_26_m1} = {read_reg(p58_26_m1)}")

# Switch back to Mode 0
print("\n=== Switching back to Mode 0 ===")
ok = write_reg(p58_33_m1, 0)
print(f"  Write P58.33=0 at Mode 1 addr {p58_33_m1}: {'OK' if ok else 'FAILED'}")
time.sleep(1)

# Verify back in Mode 0
v = read_reg(m0_addr(58, 33))
print(f"  Verify P58.33 at Mode 0 addr = {v}")

client.close()
print("\nDone.")
