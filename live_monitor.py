"""Live monitor - watch status word while changing panel settings"""
from pymodbus.client import ModbusSerialClient
import time

c = ModbusSerialClient(port='COM4', baudrate=9600, parity='E', stopbits=1, bytesize=8, timeout=1)
if not c.connect():
    print("Cannot open COM4")
    exit()

print("=" * 60)
print("  LIVE MONITOR - Change P19.11 / P19.12 on panel")
print("  Watching Status Word for changes...")
print("  Press Ctrl+C to stop")
print("=" * 60)

last_sw = None
count = 0
try:
    while True:
        r = c.read_holding_registers(address=0, count=5, device_id=1)
        if hasattr(r, 'registers'):
            sw = r.registers[2]
            cw = r.registers[0]
            spd = r.registers[3]
            cur = r.registers[4]
            
            if sw != last_sw or count % 10 == 0:
                print(f"  [{count:4d}] CW=0x{cw:04X}  StatusWord=0x{sw:04X}  Speed={spd}  Current={cur}", end="")
                if sw == 0:
                    print("  << Drive ignoring Modbus")
                elif sw & 0x0040:
                    print("  << Switch on disabled")
                elif sw & 0x0001:
                    print("  << READY!")
                else:
                    print()
                last_sw = sw
        count += 1
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    c.close()
    print("\nStopped.")
