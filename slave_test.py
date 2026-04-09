"""Quick test - both slave 1 and slave 2, raw frames"""
import serial, time

def calc_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

ser = serial.Serial('COM4', 19200, parity='E', stopbits=1, bytesize=8, timeout=2)
print("=== RAW MODBUS TEST - Slave 1 vs Slave 2 ===\n")

for slave_id in [1, 2]:
    # Read holding register 0 (40001)
    data = bytes([slave_id, 0x03, 0x00, 0x00, 0x00, 0x01])
    frame = data + calc_crc(data)
    
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)
    
    ser.write(frame)
    time.sleep(1.0)
    
    w = ser.in_waiting
    if w > 0:
        resp = ser.read(w)
        print(f"Slave {slave_id}: TX={frame.hex(' ')}")
        print(f"          RX={resp.hex(' ')} ({w} bytes)")
        if w >= 7 and resp[0] == slave_id and resp[1] == 0x03:
            val = (resp[3] << 8) | resp[4]
            print(f"          VALUE = {val} (0x{val:04X}) <<< VALID RESPONSE!")
        elif w >= 5 and resp[0] == slave_id and resp[1] == 0x83:
            print(f"          EXCEPTION code={resp[2]} (drive responded with error)")
        else:
            print(f"          Partial/echo response")
    else:
        print(f"Slave {slave_id}: No response")
    print()

ser.close()
print("Done.")
