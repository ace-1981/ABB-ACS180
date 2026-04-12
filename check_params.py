"""Check ACS180 parameters - find why speed ref isn't from Modbus."""
from pymodbus.client import ModbusSerialClient
import config

client = ModbusSerialClient(
    port=config.COM_PORT, baudrate=config.BAUD_RATE,
    parity=config.PARITY, stopbits=config.STOP_BITS,
    bytesize=config.BYTE_SIZE, timeout=2.0,
)
if not client.connect():
    print("ERROR: Cannot open COM4!")
    exit(1)

print("=== ACS180 Parameter Check ===\n")

# ABB ACS180 parameter mapping: address = group*100 + param_index
# Key groups: P19 (Operation mode), P58 (Fieldbus), P1 (Operating data)
param_groups = [
    (19, "P19 - Operation Mode", range(1, 25)),
    (58, "P58 - Fieldbus/Modbus", range(1, 15)),
    (1, "P01 - Operating Data", range(1, 20)),
    (20, "P20 - Start/Stop/Direction", range(1, 15)),
    (21, "P21 - Reference Select", range(1, 15)),
    (22, "P22 - Freq Ref Chain", range(1, 25)),
]

for group, name, params in param_groups:
    print(f"\n--- {name} ---")
    for p in params:
        addr = group * 100 + p
        try:
            res = client.read_holding_registers(address=addr, count=1, device_id=1)
            if hasattr(res, 'registers'):
                val = res.registers[0]
                # Show signed value too (some params use signed int16)
                signed = val if val < 32768 else val - 65536
                print(f"  P{group:02d}.{p:02d} (reg {addr:5d}) = {val:6d} (0x{val:04X})  signed={signed}")
        except:
            pass

# Also check regs 0-10 area
print("\n--- Fieldbus Process Data (regs 0-10) ---")
res = client.read_holding_registers(address=0, count=10, device_id=1)
if hasattr(res, 'registers'):
    for i, v in enumerate(res.registers):
        print(f"  Reg {i} = {v} (0x{v:04X})")

client.close()
print("\nDone.")
