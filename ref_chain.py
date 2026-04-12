"""Deep investigation of the reference chain."""
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

print("=== Reference Chain Investigation ===\n")

# Start motor so we can see actual freq
client.write_register(address=1, value=10000, device_id=1)
time.sleep(0.1)
client.write_register(address=0, value=config.CW_STOP, device_id=1)
time.sleep(0.3)
client.write_register(address=0, value=config.CW_RUN, device_id=1)
time.sleep(2)

# Read ALL P01 values (actual signals) while running
print("--- P01 All values (motor running, ref=10000) ---")
for base in range(101, 151, 10):
    try:
        res = client.read_holding_registers(address=base, count=10, device_id=1)
        if hasattr(res, 'registers'):
            for i, v in enumerate(res.registers):
                sv = v if v < 32768 else v - 65536
                addr = base + i
                p_num = addr - 100
                if sv != 0:
                    print(f"  P01.{p_num:02d} (reg {addr}) = {sv}")
    except:
        pass

# Read P02 - P06 (signal monitoring groups)
for grp in [2, 3, 5, 6]:
    print(f"\n--- P{grp:02d} values ---")
    for base in range(grp*100+1, grp*100+30, 10):
        try:
            res = client.read_holding_registers(address=base, count=10, device_id=1)
            if hasattr(res, 'registers'):
                for i, v in enumerate(res.registers):
                    sv = v if v < 32768 else v - 65536
                    addr = base + i
                    p_num = addr - grp*100
                    if sv != 0:
                        print(f"  P{grp:02d}.{p_num:02d} (reg {addr}) = {sv}")
        except:
            pass

# Read P19, P20, P21, P22 in detail
for grp in [19, 20, 21, 22, 28]:
    print(f"\n--- P{grp:02d} ALL values ---")
    for base in range(grp*100, grp*100+50, 10):
        try:
            res = client.read_holding_registers(address=base, count=10, device_id=1)
            if hasattr(res, 'registers'):
                for i, v in enumerate(res.registers):
                    addr = base + i
                    p_num = addr - grp*100
                    sv = v if v < 32768 else v - 65536
                    if sv != 0:
                        print(f"  P{grp:02d}.{p_num:02d} (reg {addr}) = {v:6d} / signed={sv}")
        except:
            pass

# P58 Fieldbus params
print(f"\n--- P58 Fieldbus ---")
for base in range(5800, 5830, 10):
    try:
        res = client.read_holding_registers(address=base, count=10, device_id=1)
        if hasattr(res, 'registers'):
            for i, v in enumerate(res.registers):
                addr = base + i
                p_num = addr - 5800
                sv = v if v < 32768 else v - 65536
                if sv != 0:
                    print(f"  P58.{p_num:02d} (reg {addr}) = {v:6d} / signed={sv}")
    except:
        pass

# Now try changing speed while running and see what happens
print("\n\n--- Speed change test ---")
for speed in [2000, 6000, 10000, 16000, 20000]:
    client.write_register(address=1, value=speed, device_id=1)
    time.sleep(3)
    r0 = client.read_holding_registers(address=0, count=6, device_id=1)
    # Read P01.01 area
    p1 = client.read_holding_registers(address=101, count=19, device_id=1)
    p1v = [v if v < 32768 else v - 65536 for v in p1.registers] if hasattr(p1, 'registers') else []
    nz = {f"P01.{i+1:02d}": v for i, v in enumerate(p1v) if v != 0}
    ref_back = r0.registers[1]
    print(f"  Wrote {speed:5d} -> reads {ref_back:5d} | {nz}")

client.write_register(address=0, value=config.CW_STOP, device_id=1)
client.close()
print("\nDone.")
