"""Aggressive raw test - long wait, multiple attempts, flush carefully"""
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

ser = serial.Serial('COM4', 19200, parity='E', stopbits=1, bytesize=8, timeout=3)
print("=== AGGRESSIVE COMMUNICATION TEST ===")
print(f"Port: {ser.name} @ {ser.baudrate}/8{ser.parity}{ser.stopbits}\n")

# Flush everything
ser.reset_input_buffer()
ser.reset_output_buffer()
time.sleep(0.5)

# Drain any stale data
stale = ser.read(100)
if stale:
    print(f"Drained stale data: {stale.hex(' ')}\n")

for slave_id in [2, 1]:
    print(f"--- Slave {slave_id} ---")
    data = bytes([slave_id, 0x03, 0x00, 0x00, 0x00, 0x01])
    frame = data + calc_crc(data)
    
    for attempt in range(3):
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        ser.write(frame)
        ser.flush()  # Ensure all bytes are sent
        
        # Wait and collect ALL bytes that come in
        time.sleep(0.1)
        total_resp = b""
        for _ in range(20):  # Check 20 times over 2 seconds
            w = ser.in_waiting
            if w > 0:
                total_resp += ser.read(w)
            time.sleep(0.1)
        
        if len(total_resp) > 0:
            print(f"  Attempt {attempt+1}: TX={frame.hex(' ')}")
            print(f"               RX={total_resp.hex(' ')} ({len(total_resp)} bytes)")
            
            # Check if it's more than just echo
            if len(total_resp) >= 5:
                print(f"               >>> REAL RESPONSE!")
                break
        else:
            print(f"  Attempt {attempt+1}: No response at all")
    print()

# Also try: is the echo the first byte of OUR frame bouncing back?
print("--- ECHO ANALYSIS ---")
ser.reset_input_buffer()
test_frame = bytes([0xAA, 0x03, 0x00, 0x00, 0x00, 0x01])
test_frame += calc_crc(test_frame)
ser.write(test_frame)
time.sleep(0.5)
w = ser.in_waiting
if w > 0:
    resp = ser.read(w)
    print(f"Sent 0xAA..., got back: {resp.hex(' ')}")
    if resp[0] == 0xAA:
        print(">>> Echo confirmed: adapter echoes TX back to RX")
        print(">>> This means the KA301 has echo enabled or wiring loops TX to RX")
    elif resp[0] == 0x00:
        print(">>> Getting 0x00 regardless - this is line noise, not echo")
else:
    print("No response to 0xAA frame either")

ser.close()
print("\nDone.")
