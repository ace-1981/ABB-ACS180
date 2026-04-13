"""Fix motor noise: set correct 1.35A current, redo ID run."""
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
    print('  P{:02d}.{:02d}: {} -> {}  [{}]'.format(g, i, v, rb, ok))
    return rb == v

def write_reg(addr, val):
    r = client.write_register(address=addr, value=val, device_id=1)
    return not (hasattr(r, 'isError') and r.isError())

print('=== Current Motor Settings ===')
for g, i, name in [(99,4,'Ctrl mode'),(99,6,'Nom current'),(99,7,'Voltage'),
                     (99,8,'Freq'),(99,9,'Speed'),(99,10,'Power'),
                     (97,1,'SW freq ref'),(97,2,'SW freq actual'),
                     (30,17,'Max current')]:
    v = read_p(g, i)
    print('  P{:02d}.{:02d} ({}) = {}'.format(g, i, name, v))
    time.sleep(0.1)

# Test: what values does P99.06 accept for finer resolution?
print()
print('=== Testing P99.06 Resolution ===')
# The 16-bit register seems to use 1A per unit
# But let's try intermediate values to see if 0.1A works
for test_val in [1, 2, 10, 13, 14, 15]:
    write_p(99, 6, test_val)
    time.sleep(0.2)

# Try: maybe the drive has internal scaling we missed
# Read as 2 consecutive regs
print()
print('=== P99.06 as 32-bit when set to different values ===')
for test_val in [1, 2, 4]:
    write_p(99, 6, test_val)
    time.sleep(0.2)
    addr = 99 * 100 + 6 - 1
    r = client.read_holding_registers(address=addr, count=2, device_id=1)
    if hasattr(r, 'registers'):
        print('    32-bit regs: {}'.format(r.registers))

# Check P46.05 and P46.44 again
print()
print('=== Scaling Parameters ===')
v = read_p(46, 5)
print('  P46.05 (Current scaling) = {}'.format(v))
v = read_p(46, 44)
print('  P46.44 (Current decimals) = {}'.format(v))

# Check the actual RANGE the drive allows for P99.06
# Try small values
print()
print('=== Finding P99.06 valid range ===')
# Max allowed for this drive:
# vector: 1/6..2 x IN = 0.67..8A (for 4A drive)
# Let's find boundaries
for test_val in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16]:
    addr = 99 * 100 + 6 - 1
    r = client.write_register(address=addr, value=test_val, device_id=1)
    is_err = hasattr(r, 'isError') and r.isError()
    time.sleep(0.2)
    rb = read_p(99, 6)
    clamped = '' if rb == test_val else ' -> CLAMPED to {}'.format(rb)
    print('  Write {} err={}  readback={}{}'.format(test_val, is_err, rb, clamped))

# Restore
write_p(99, 6, 2)
print()

# Check switching freq options
print('=== P97.01 Switching Freq Options ===')
for test_val in [4, 8, 12, 16]:
    write_p(97, 1, test_val)
    time.sleep(0.3)
    actual = read_p(97, 2)
    print('    P97.02 (actual) = {}'.format(actual))

client.close()
