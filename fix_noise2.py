"""Fix motor noise: correct current to 1.35A, redo ID run, optimize settings."""
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

def write_reg(addr, val):
    r = client.write_register(address=addr, value=val, device_id=1)
    return not (hasattr(r, 'isError') and r.isError())

print('===============================================')
print(' Motor Noise Fix - Correct Current & Redo ID Run')
print('===============================================')
print(' Motor: 1.35A, 230V, 50Hz, 1350rpm, 0.25kW')
print()

# === Step 1: Fix P46.05 scaling for better current resolution ===
# P46.05=10000 means 1 unit = 1A (too coarse for 1.35A)
# Change to P46.05=1000 -> 1 unit = 0.1A -> can set 14 for 1.4A
# BUT this changes all current parameter scaling!
# SAFER: try using scalar approach with P46.05 = 100
# 100A = 10000 -> 1 unit = 0.01A -> 135 = 1.35A

print('Step 1: Change current scaling for finer resolution')
print('  Current P46.05 = {}'.format(read_p(46, 5)))

# First test: change P46.05 from 10000 to 100 (0.01A per unit)
write_p(46, 5, 100)
time.sleep(0.5)

# Now P99.06 should need 135 for 1.35A
print()
print('Step 2: Set motor current to 1.35A (135 * 0.01A)')
write_p(99, 6, 135)

# Read back to verify
time.sleep(0.3)
cur = read_p(99, 6)
print('  P99.06 readback = {} (should be 135 = 1.35A)'.format(cur))

# If that didn't work (clamped), revert and use integer
if cur != 135:
    print('  Fine resolution FAILED - reverting to P46.05=10000')
    write_p(46, 5, 10000)
    time.sleep(0.3)
    # Set P99.06 = 1 (1.0A, closest integer to 1.35A)
    print('  Setting P99.06 = 1 (1.0A, closest available)')
    write_p(99, 6, 1)
else:
    print('  Fine current 1.35A set successfully!')

# Also reduce max current accordingly
print()
print('Step 3: Reduce max current (P30.17)')
# Max current should be ~150% of motor nominal
# With P46.05=100: 200 = 2.0A; with P46.05=10000: 2 = 2.0A
p46_05 = read_p(46, 5)
if p46_05 == 100:
    write_p(30, 17, 200)  # 2.0A max
else:
    write_p(30, 17, 2)    # 2A max

# Verify motor parameters
print()
print('Step 4: Verify all motor parameters')
for g, i, name in [(99,3,'Type'),(99,4,'Ctrl mode'),(99,6,'Current'),
                     (99,7,'Voltage'),(99,8,'Freq'),(99,9,'Speed'),
                     (99,10,'Power'),(97,1,'SW freq ref'),(30,17,'Max current'),
                     (46,5,'Current scaling')]:
    v = read_p(g, i)
    print('  P{:02d}.{:02d} ({}) = {}'.format(g, i, name, v))
    time.sleep(0.1)

# === Step 5: Redo Standstill ID Run ===
print()
print('Step 5: Request Standstill ID Run (required after changing current)')
write_p(99, 13, 3)  # 3 = Standstill

w = read_p(4, 6)
if w:
    print('  Warning: 0x{:04X}'.format(w))

print()
print('Step 6: Execute ID Run...')
write_reg(0, 0x047E)  # STOP first
time.sleep(1.0)
write_reg(0, 0x047F)  # RUN -> triggers ID run
print('  START sent')

start = time.time()
last = ''
for i in range(60):
    time.sleep(1.0)
    p13 = read_p(99, 13)
    p14 = read_p(99, 14)
    fault = read_p(4, 1)
    elapsed = time.time() - start

    state = 'P99.13={} P99.14={}'.format(p13, p14)
    if fault and fault > 0:
        state += ' FAULT=0x{:04X}'.format(fault)
    if state != last:
        print('  [{:5.1f}s] {}'.format(elapsed, state))
        last = state

    if fault and fault > 0:
        print('  FAULT! Resetting...')
        write_reg(0, 0x04FF)  # fault reset
        time.sleep(1.0)
        write_reg(0, 0x047E)  # stop
        break

    if p13 == 0 and i > 2:
        print('  ID run COMPLETED at {:.1f}s!'.format(elapsed))
        break

write_reg(0, 0x047E)  # stop
time.sleep(1.0)

# === Step 7: Save to NVM ===
print()
print('Step 7: Saving to NVM...')
write_reg(96 * 100 + 7 - 1, 1)
time.sleep(2.0)
val = read_p(96, 7)
print('  NVM: {}'.format('Done' if val == 0 else 'Pending'))

# === Step 8: Motor model results ===
print()
print('Step 8: Motor Model After ID Run')
for idx in range(1, 15):
    val = read_p(98, idx)
    if val is not None and val > 0:
        print('  P98.{:02d} = {}'.format(idx, val))
    time.sleep(0.1)

# === Step 9: Test motor ===
print()
print('Step 9: Quick Motor Test at 30%')
write_reg(1, 6000)
time.sleep(0.2)
write_reg(0, 0x047F)

for i in range(8):
    time.sleep(1.0)
    r = client.read_holding_registers(address=3, count=3, device_id=1)
    if hasattr(r, 'registers'):
        sw, a1, a2 = r.registers[0], r.registers[1], r.registers[2]
        print('  [{}s] SW=0x{:04X} Speed={} Current={}'.format(i+1, sw, a1, a2))

write_reg(0, 0x047E)
time.sleep(2)
print('  Motor stopped')

# Final status
print()
print('=== Final Configuration ===')
for g, i, name in [(99,4,'Ctrl mode'),(99,6,'Nom current'),(99,9,'Speed'),
                     (97,1,'SW freq'),(30,17,'Max current'),(99,13,'ID run req'),
                     (99,14,'Last ID run'),(46,5,'Curr scaling')]:
    v = read_p(g, i)
    print('  P{:02d}.{:02d} ({}) = {}'.format(g, i, name, v))
    time.sleep(0.1)

client.close()
print()
print('DONE! Check if magnetic noise is reduced.')
