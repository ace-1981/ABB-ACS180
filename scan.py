"""Deep scan for ABB ACS180 on COM4"""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import sys

port = 'COM4'
bauds = [9600, 19200, 38400, 57600, 115200]
parities = [('Even','E'), ('None','N'), ('Odd','O')]
slave_ids = [1, 2, 3, 4, 5, 10, 16, 247]
test_regs = [0, 1, 2, 3, 100, 400, 1000, 2000, 4000]

print('='*60)
print('  DEEP SCAN - ABB ACS180 on COM4')
print('  Testing all combinations...')
print('='*60)
total = len(bauds) * len(parities) * len(slave_ids) * len(test_regs)
count = 0
found = False

for baud in bauds:
    for pname, pval in parities:
        client = ModbusSerialClient(port=port, baudrate=baud, parity=pval, stopbits=1, bytesize=8, timeout=0.3, retries=1)
        if not client.connect():
            client.close()
            continue
        for sid in slave_ids:
            for reg in test_regs:
                count += 1
                if count % 50 == 0:
                    print(f'  Scanning... {count}/{total}', end='\r')
                    sys.stdout.flush()
                try:
                    result = client.read_holding_registers(address=reg, count=1, device_id=sid)
                    if hasattr(result, 'registers'):
                        print(f'\n  >>> FOUND! Baud={baud} Parity={pname} Slave={sid} Reg={reg} = {result.registers[0]} (0x{result.registers[0]:04X})')
                        found = True
                        try:
                            more = client.read_holding_registers(address=0, count=10, device_id=sid)
                            if hasattr(more, 'registers'):
                                print(f'      Regs 0-9: {[hex(r) for r in more.registers]}')
                        except: pass
                except (ModbusIOException, Exception):
                    pass
                if found:
                    break
            if found:
                break
        client.close()
        if found:
            break
    if found:
        break

if not found:
    print(f'\n  Scanned {count} combinations - NO RESPONSE.')
    print()
    print('  The drive is NOT responding to Modbus.')
    print('  Modbus must be enabled on the drive panel first.')
print('='*60)
