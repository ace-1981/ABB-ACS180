"""Enable EFB properly: Set P58.01=1 (Modbus RTU) and verify all config."""
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

# Stop motor
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(1)

print("=== Reading ALL P58 parameters ===")
for idx in range(1, 40):
    addr = 5800 + idx
    v = read_reg(addr)
    if v is not None:
        print(f"  P58.{idx:02d} (addr {addr}) = {v} (0x{v:04X})")

print("\n=== P20.01-P20.10 (Command sources) ===")
for idx in range(1, 11):
    v = read_reg(2000 + idx)
    if v is not None:
        print(f"  P20.{idx:02d} = {v}")

# Check what value 1 means for P20.01
# Manual says: Ext1 commands source
# Values: DI (various), EFB, etc.
print("\n  P20.01=1 might be DI1 as command source")

print("\n=== Enable EFB: P58.01 = 1 (Modbus RTU) ===")
print(f"  Current P58.01 = {read_reg(5801)}")

# Try writing 1
ok = write_reg(5801, 1)
print(f"  Write P58.01 = 1: {'OK' if ok else 'FAILED'}")
time.sleep(0.5)
print(f"  Verify P58.01 = {read_reg(5801)}")

# Try refresh (P58.06)
print("\n  Trying P58.06 refresh...")
# P58.06 values: 0=Enabled, 1=Refresh, 2=Silent
ok = write_reg(5806, 1)
print(f"  Write P58.06 = 1 (Refresh): {'OK' if ok else 'FAILED'}")
time.sleep(2)
print(f"  P58.06 after refresh = {read_reg(5806)}")

# Check P03.09 again  
print(f"\n  P03.09 (EFB Ref1) = {signed(read_reg(309))}")

# Try writing ref and check
client.write_register(address=1, value=12345, device_id=1)
time.sleep(0.5)
print(f"  Wrote 12345 to reg 1 -> P03.09 = {signed(read_reg(309))}")

# Now check P20 - need to set Ext1 commands to EFB
print("\n=== P20 Command Source Settings ===")
# Search manual for P20.01 values
# Let's read the full P20 group and look for EFB values
for idx in range(1, 30):
    v = read_reg(2000 + idx)
    if v is not None:
        print(f"  P20.{idx:02d} = {v}")

# Also read P19 (operating mode)
print("\n=== P19 Operating Mode ===")
for idx in range(1, 20):
    v = read_reg(1900 + idx)
    if v is not None:
        print(f"  P19.{idx:02d} = {v}")

# Read full register dump while reference is set
print("\n=== Register 0-13 ===")
res = client.read_holding_registers(address=0, count=14, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        sv = v if v < 32768 else v - 65536
        print(f"  Reg[{i:2d}] = {v:6d} (0x{v:04X}) signed={sv}")

client.close()
print("\nDone.")
