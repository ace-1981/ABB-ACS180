"""Fix motor magnetic noise - apply all recommended changes."""
from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(port='COM4', baudrate=19200, parity='E', stopbits=1, bytesize=8, timeout=2)
client.connect()

def read_p(g, i):
    addr = g * 100 + i - 1
    r = client.read_holding_registers(address=addr, count=1, device_id=1)
    if hasattr(r, 'registers') and len(r.registers) > 0:
        return r.registers[0]
    return None

def write_p(g, i, v):
    addr = g * 100 + i - 1
    r = client.write_register(address=addr, value=v, device_id=1)
    is_err = hasattr(r, 'isError') and r.isError()
    time.sleep(0.3)
    rb = read_p(g, i)
    ok = 'OK' if rb == v else 'FAIL(got {})'.format(rb)
    print('  P{:02d}.{:02d} = {}  [{}]'.format(g, i, v, ok))
    return rb == v

print('=== Fixing Noise Parameters ===')
print()

# 1. Switching frequency: 4kHz -> 12kHz (much quieter)
print('1. Switching frequency 4kHz -> 12kHz')
write_p(97, 1, 12)

# 2. Magnetization time: 500ms -> 100ms (shorter pre-mag buzz)
print('2. Magnetization time 500ms -> 100ms')
write_p(21, 2, 100)

# 3. Max current: 11A -> 4A (drive default was way too high for 2A motor)
print('3. Max current 11A -> 4A')
write_p(30, 17, 4)

# 4. IR compensation: 4 -> 0 (disable in vector mode)
print('4. IR compensation -> 0 (disable)')
write_p(97, 13, 0)

# Save to NVM
print()
print('=== Saving to NVM ===')
addr_save = 96 * 100 + 7 - 1
r = client.write_register(address=addr_save, value=1, device_id=1)
time.sleep(2.0)
val = read_p(96, 7)
status = 'Done' if val == 0 else 'Pending'
print('  NVM save: ' + status)

# Verify all
print()
print('=== Verification ===')
params = [
    (97, 1, 'Switching freq ref'),
    (97, 2, 'Switching freq actual'),
    (21, 2, 'Magnetization time'),
    (30, 17, 'Max current'),
    (97, 13, 'IR compensation'),
]
for g, i, name in params:
    v = read_p(g, i)
    print('  P{:02d}.{:02d} ({}) = {}'.format(g, i, name, v))
    time.sleep(0.1)

# Quick motor test
print()
print('=== Quick Motor Test (30% speed, 8 seconds) ===')
client.write_register(address=1, value=6000, device_id=1)  # 30%
time.sleep(0.2)
client.write_register(address=0, value=0x047F, device_id=1)  # RUN

for i in range(8):
    time.sleep(1.0)
    r = client.read_holding_registers(address=3, count=3, device_id=1)
    if hasattr(r, 'registers'):
        sw, a1, a2 = r.registers[0], r.registers[1], r.registers[2]
        print('  [{}s] SW=0x{:04X} Speed={} Current={}'.format(i+1, sw, a1, a2))

# Stop
client.write_register(address=0, value=0x047E, device_id=1)
time.sleep(2)
print('  Motor stopped')

client.close()
print()
print('Done! Check if noise is reduced.')
