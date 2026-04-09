"""Loopback test - check if USB-to-RS485 converter is working"""
import serial
import time

PORT = "COM4"

print("=" * 50)
print("  LOOPBACK TEST - COM4")
print("=" * 50)
print("  A and B should be shorted together")
print()

try:
    ser = serial.Serial(PORT, 9600, parity="N", stopbits=1, bytesize=8, timeout=1)
    print(f"  Port open: OK")

    # Send test data
    test_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0xAA, 0xBB, 0xCC])
    print(f"  Sending: {test_data.hex(' ')}")
    
    ser.reset_input_buffer()
    ser.write(test_data)
    time.sleep(0.3)

    rx_count = ser.in_waiting
    print(f"  Bytes received back: {rx_count}")

    if rx_count > 0:
        rx_data = ser.read(rx_count)
        print(f"  Received: {rx_data.hex(' ')}")
        if rx_data == test_data:
            print()
            print("  ========================================")
            print("  =   CONVERTER IS WORKING! (ECHO OK)   =")
            print("  ========================================")
            print()
            print("  The converter sends and receives fine.")
            print("  Problem is between converter and drive.")
        else:
            print()
            print("  Got data back but it's different.")
            print("  Converter may have issues.")
    else:
        print()
        print("  ========================================")
        print("  =   NO ECHO - CONVERTER PROBLEM!      =")
        print("  ========================================")
        print()
        print("  The converter is NOT sending data.")
        print("  Try:")
        print("  - Different USB port")
        print("  - Update converter driver")
        print("  - Replace converter")

    ser.close()
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 50)
