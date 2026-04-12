"""Try reading actual values as INPUT registers + check local/remote mode."""
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

print("=== Input Registers vs Holding Registers Test ===\n")

# Start motor
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
time.sleep(3)

# 1) Read registers 0-20 as HOLDING registers (FC03)
print("--- Registers 0-20 as HOLDING (FC03) ---")
res = client.read_holding_registers(address=0, count=20, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        sv = v if v < 32768 else v - 65536
        if v != 0:
            print(f"  HR[{i:3d}] = {v:6d} (0x{v:04X}) signed={sv}")

# 2) Read registers 0-20 as INPUT registers (FC04)
print("\n--- Registers 0-20 as INPUT (FC04) ---")
res = client.read_input_registers(address=0, count=20, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        sv = v if v < 32768 else v - 65536
        if v != 0:
            print(f"  IR[{i:3d}] = {v:6d} (0x{v:04X}) signed={sv}")
else:
    print(f"  Error: {res}")

# 3) Read P01 as INPUT registers
print("\n--- P01 (101-120) as INPUT (FC04) ---")
res = client.read_input_registers(address=101, count=20, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        sv = v if v < 32768 else v - 65536
        if v != 0:
            print(f"  IR[{101+i}] P01.{i+1:02d} = {v:6d} signed={sv}")
else:
    print(f"  Error: {res}")

# 4) Read P01 as HOLDING registers (for comparison)
print("\n--- P01 (101-120) as HOLDING (FC03) ---")
res = client.read_holding_registers(address=101, count=20, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        sv = v if v < 32768 else v - 65536
        if v != 0:
            print(f"  HR[{101+i}] P01.{i+1:02d} = {v:6d} signed={sv}")
else:
    print(f"  Error: {res}")

# 5) Try wider range of input registers
print("\n--- Input registers 0-100 scan ---")
for base in range(0, 100, 10):
    res = client.read_input_registers(address=base, count=10, device_id=1)
    if hasattr(res, 'registers'):
        for i, v in enumerate(res.registers):
            sv = v if v < 32768 else v - 65536
            if v != 0:
                print(f"  IR[{base+i:3d}] = {v:6d} (0x{v:04X}) signed={sv}")

# 6) Check Status Word bits in detail
r = client.read_holding_registers(address=0, count=6, device_id=1)
if hasattr(r, 'registers'):
    sw = r.registers[3]
    cw = r.registers[0]
    ref = r.registers[1]
    print(f"\n--- Status Analysis ---")
    print(f"CW = 0x{cw:04X} = {cw:016b}")
    print(f"SW = 0x{sw:04X} = {sw:016b}")
    print(f"Ref = {ref}")
    print(f"  SW bits:")
    labels = {0:"ReadyToSwitchOn", 1:"SwitchedOn", 2:"OperationEnabled",
              3:"Fault", 4:"VoltageEnabled", 5:"QuickStop",
              6:"SwitchOnDisabled", 7:"Warning",
              8:"ControlRequested", 9:"RemoteControl",
              10:"TargetReached", 11:"InternalLimitActive",
              12:"Bit12", 13:"Bit13", 14:"Bit14", 15:"Bit15"}
    for bit in range(16):
        val = (sw >> bit) & 1
        if val:
            print(f"    Bit {bit:2d}: {labels.get(bit, f'Bit{bit}')} = {val}")

# 7) Check Local/Remote: try writing CW with bit 9 (Remote) 
# In ABB, Status Word bit 9 = 1 means Remote mode
# If it's 0, we might be in Local mode and fieldbus reference is ignored
print(f"\n  SW Bit 9 (RemoteControl) = {(sw>>9)&1}")
if not ((sw >> 9) & 1):
    print("  WARNING: Drive appears to be in LOCAL mode!")
    print("  Fieldbus reference may be ignored!")

# 8) Try reading actual speed from different register addresses
# Some ABB drives use register 1 for speed ref (write) and register 3 for status
# But actual output frequency might be at different addresses
print("\n--- Wide Holding Register Scan (while running) ---")
for base in range(0, 50, 10):
    res = client.read_holding_registers(address=base, count=10, device_id=1)
    if hasattr(res, 'registers'):
        for i, v in enumerate(res.registers):
            sv = v if v < 32768 else v - 65536
            if v != 0:
                addr = base + i
                print(f"  HR[{addr:3d}] = {v:6d} (0x{v:04X}) signed={sv}")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
print("\nMotor stopped.")
client.close()
