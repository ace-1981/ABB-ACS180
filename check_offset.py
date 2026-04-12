"""Test address offset: Are we off by one?
Manual: Register addr = 400000 + 100*group + index
Modbus: Register 400001 = PDU address 0
Therefore: PDU address = 100*group + index - 1
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

def signed(v):
    if v is None: return 'N/A'
    return v if v < 32768 else v - 65536

print("=== Testing Address Offset ===\n")

# Test with P58.03 (Node address) - should match our slave_id=1
# Offset 0: addr = 5803
# Offset -1: addr = 5802
print("P58.03 (Node address - should be 1 to match slave_id):")
print(f"  addr 5803 (offset 0) = {read_reg(5803)}")
print(f"  addr 5802 (offset -1) = {read_reg(5802)}")

# Test with P58.05 (Parity - should be 0 for 8 EVEN 1)
print("\nP58.05 (Parity - should be 0 for EVEN):")
print(f"  addr 5805 (offset 0) = {read_reg(5805)}")
print(f"  addr 5804 (offset -1) = {read_reg(5804)}")

# Test P58.02 (Protocol ID - read-only status, large number expected)
print("\nP58.02 (Protocol ID):")
print(f"  addr 5802 (offset 0) = {read_reg(5802)}")
print(f"  addr 5801 (offset -1) = {read_reg(5801)}")

# Test P58.01 (Protocol enable - should be 1 for Modbus RTU)
print("\nP58.01 (Protocol enable - should be 1=Modbus RTU):")
print(f"  addr 5801 (offset 0) = {read_reg(5801)}")
print(f"  addr 5800 (offset -1) = {read_reg(5800)}")

# Test P20.01 (should be 14=EFB, or 1=DI)
print("\nP20.01 (Ext1 commands):")
print(f"  addr 2001 (offset 0) = {read_reg(2001)}")
print(f"  addr 2000 (offset -1) = {read_reg(2000)}")

# Read block around P20 to see the pattern
print("\n=== P20 block (addrs 1999-2010) ===")
for addr in range(1999, 2011):
    v = read_reg(addr)
    idx_off0 = addr - 2000
    idx_off1 = addr - 1999
    print(f"  addr {addr}: val={v}  (offset0: P20.{idx_off0:02d}, offset-1: P20.{idx_off1:02d})")

# Read P03.09 (EFB Ref1) with both offsets
print("\n=== P03.09 (EFB Reference 1) ===")
# Write 12345 to register 1 first
client.write_register(address=1, value=12345, device_id=1)
time.sleep(0.3)
print(f"  Wrote 12345 to register 1 (Ref1)")
print(f"  addr 309 (offset 0) = {signed(read_reg(309))}")
print(f"  addr 308 (offset -1) = {signed(read_reg(308))}")

# Write different value to see which changes
client.write_register(address=1, value=5555, device_id=1)
time.sleep(0.3)
print(f"\n  Wrote 5555 to register 1")
print(f"  addr 309 (offset 0) = {signed(read_reg(309))}")
print(f"  addr 308 (offset -1) = {signed(read_reg(308))}")

# P22.11 check
print("\n=== P22.11 (Ext1 speed ref1) ===")
print(f"  addr 2211 (offset 0) = {read_reg(2211)}")
print(f"  addr 2210 (offset -1) = {read_reg(2210)}")

# Now check P01.07 (Output freq) and P01.08 (Output current)
# Start motor to see
client.write_register(address=1, value=10000, device_id=1)
client.write_register(address=0, value=0x047F, device_id=1)
time.sleep(3)

print("\n=== P01 monitoring (motor running) ===")
for addr in range(100, 120):
    v = read_reg(addr)
    sv = signed(v)
    idx_off0 = addr - 100
    idx_off1 = addr - 99
    if v is not None and v != 0:
        print(f"  addr {addr}: val={v} signed={sv}  (offset0: P01.{idx_off0:02d}, offset-1: P01.{idx_off1:02d})")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
client.close()
print("\nDone.")
