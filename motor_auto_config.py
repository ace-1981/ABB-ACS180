"""
ABB ACS180 - Motor Auto-Configuration
======================================
Sets motor nameplate values, switches to vector control,
performs standstill ID run, and saves to NVM.

Usage:
  py motor_auto_config.py              # Use defaults for Siemens 0.25kW
  py motor_auto_config.py --current 2 --power 3 --voltage 2300 --freq 500 --speed 1350
"""
import argparse
import time
import sys
from pymodbus.client import ModbusSerialClient
from config import COM_PORT, BAUD_RATE, PARITY, STOP_BITS, BYTE_SIZE, SLAVE_ID, TIMEOUT

# ── Defaults for Siemens 0.25kW 4-pole 230V Delta ──
DEFAULTS = {
    'motor_type': 0,        # 0=Induction, 1=PM
    'ctrl_mode': 0,         # 0=Vector, 1=Scalar
    'current': 2,           # Nominal current (A) - Modbus integer, ~2A
    'voltage': 2300,        # Nominal voltage (10=1V) → 230.0V
    'frequency': 500,       # Nominal frequency (10=1Hz) → 50.0Hz
    'speed': 1350,          # Nominal speed (rpm)
    'power': 3,             # Nominal power (1=0.1kW) → 0.3kW
    'cos_phi': 0,           # cos phi (100=1.0) - 0 means unknown
    'id_run_type': 3,       # 3=Standstill, 1=Normal, 2=Reduced
}


def param_addr(group, index):
    return group * 100 + index - 1


class MotorConfigurator:
    def __init__(self):
        self.client = ModbusSerialClient(
            port=COM_PORT, baudrate=BAUD_RATE, parity=PARITY,
            stopbits=STOP_BITS, bytesize=BYTE_SIZE, timeout=TIMEOUT
        )

    def connect(self):
        if not self.client.connect():
            print("ERROR: Cannot connect to drive on", COM_PORT)
            sys.exit(1)
        print(f"Connected to drive on {COM_PORT}")

    def close(self):
        self.client.close()

    def read_param(self, group, index):
        addr = param_addr(group, index)
        r = self.client.read_holding_registers(address=addr, count=1, device_id=SLAVE_ID)
        if hasattr(r, 'registers') and len(r.registers) > 0:
            return r.registers[0]
        return None

    def write_param(self, group, index, value):
        addr = param_addr(group, index)
        r = self.client.write_register(address=addr, value=value, device_id=SLAVE_ID)
        is_err = hasattr(r, 'isError') and r.isError()
        time.sleep(0.3)
        rb = self.read_param(group, index)
        return rb == value

    def read_reg(self, addr):
        r = self.client.read_holding_registers(address=addr, count=1, device_id=SLAVE_ID)
        if hasattr(r, 'registers') and len(r.registers) > 0:
            return r.registers[0]
        return None

    def write_reg(self, addr, value):
        r = self.client.write_register(address=addr, value=value, device_id=SLAVE_ID)
        return not (hasattr(r, 'isError') and r.isError())

    def save_nvm(self):
        """Save parameters to NVM (P96.07 = 1)."""
        self.write_reg(param_addr(96, 7), 1)
        time.sleep(2.0)
        val = self.read_param(96, 7)
        return val == 0  # Resets to 0 when done

    def check_faults(self):
        fault = self.read_param(4, 1)
        if fault and fault > 0:
            print(f"  FAULT: 0x{fault:04X}")
            return True
        return False

    def set_motor_params(self, cfg):
        """Set motor nameplate parameters (Group 99)."""
        print("\n=== Setting Motor Parameters ===")
        params = [
            (99, 3, cfg['motor_type'], 'Motor type (0=Induction)'),
            (99, 6, cfg['current'], f'Nominal current ({cfg["current"]}A)'),
            (99, 7, cfg['voltage'], f'Nominal voltage ({cfg["voltage"]/10:.1f}V)'),
            (99, 8, cfg['frequency'], f'Nominal frequency ({cfg["frequency"]/10:.1f}Hz)'),
            (99, 9, cfg['speed'], f'Nominal speed ({cfg["speed"]} rpm)'),
            (99, 10, cfg['power'], f'Nominal power ({cfg["power"]*0.1:.1f}kW)'),
            (99, 11, cfg['cos_phi'], f'Cos phi ({cfg["cos_phi"]/100:.2f})'),
        ]
        all_ok = True
        for group, index, value, desc in params:
            ok = self.write_param(group, index, value)
            status = "OK" if ok else "FAIL"
            print(f"  P{group}.{index:02d} = {value:5d}  ({desc}) [{status}]")
            if not ok:
                all_ok = False
        return all_ok

    def set_vector_mode(self):
        """Switch to vector control mode."""
        print("\n=== Setting Vector Control Mode ===")
        ok = self.write_param(99, 4, 0)
        print(f"  P99.04 = 0 (Vector) [{'OK' if ok else 'FAIL'}]")
        return ok

    def request_id_run(self, id_type=3):
        """Request motor identification run."""
        names = {0: 'None', 1: 'Normal', 2: 'Reduced', 3: 'Standstill', 4: 'Advanced'}
        print(f"\n=== Requesting {names.get(id_type, '?')} ID Run ===")
        ok = self.write_param(99, 13, id_type)
        print(f"  P99.13 = {id_type} [{'OK' if ok else 'FAIL'}]")

        # Check for warning AFF6
        w = self.read_param(4, 6)
        if w == 0xAFF6:
            print("  Warning AFF6: 'Motor ID run will occur at next start' - expected!")
        return ok

    def execute_id_run(self, timeout_sec=60):
        """Send START to trigger ID run and monitor until completion."""
        print(f"\n=== Executing ID Run (timeout {timeout_sec}s) ===")

        # Ensure stopped
        self.write_reg(0, 0x047E)
        time.sleep(1.0)

        # Send RUN
        self.write_reg(0, 0x047F)
        print("  START command sent")

        start = time.time()
        last_state = ''
        success = False

        for i in range(timeout_sec):
            time.sleep(1.0)
            sw = self.read_reg(3)
            p13 = self.read_param(99, 13)
            p14 = self.read_param(99, 14)
            fault = self.read_param(4, 1)
            elapsed = time.time() - start

            sw_str = f'0x{sw:04X}' if sw else 'N/A'
            state = f'SW={sw_str} P99.13={p13} P99.14={p14}'
            if state != last_state:
                print(f"  [{elapsed:5.1f}s] {state}")
                last_state = state

            if fault and fault > 0:
                print(f"  FAULT at {elapsed:.1f}s: 0x{fault:04X}")
                break

            if p13 == 0 and i > 2:
                print(f"  ID run completed at {elapsed:.1f}s! Last run type={p14}")
                success = True
                break

        # Stop motor
        self.write_reg(0, 0x047E)
        time.sleep(1.0)
        return success

    def verify_config(self):
        """Print current motor configuration."""
        print("\n=== Current Motor Configuration ===")
        labels = {
            3: 'Type', 4: 'Ctrl Mode', 6: 'Current(A)',
            7: 'Voltage(*10V)', 8: 'Freq(*10Hz)', 9: 'Speed(rpm)',
            10: 'Power(*0.1kW)', 11: 'CosP(*100)', 13: 'ID Run Req',
            14: 'Last ID Run', 15: 'Pole Pairs', 16: 'Phase Order',
        }
        for idx in sorted(labels.keys()):
            val = self.read_param(99, idx)
            print(f"  P99.{idx:02d} ({labels[idx]:16s}) = {val}")
            time.sleep(0.1)

    def test_motor(self, speed_pct=30, duration=5):
        """Brief motor test at given speed percentage."""
        print(f"\n=== Motor Test at {speed_pct}% for {duration}s ===")
        ref = int(speed_pct / 100.0 * 20000)
        self.write_reg(1, ref)
        self.write_reg(0, 0x047F)

        for i in range(duration):
            time.sleep(1.0)
            sw = self.read_reg(3)
            a1 = self.read_reg(4)
            running = bool(sw & 0x0004) if sw else False
            print(f"  [{i+1}s] Speed={a1} Running={running}")

        self.write_reg(0, 0x047E)
        time.sleep(2.0)
        print("  Motor stopped")


def main():
    parser = argparse.ArgumentParser(description='ABB ACS180 Motor Auto-Configuration')
    parser.add_argument('--current', type=int, default=DEFAULTS['current'],
                        help='Motor nominal current in Modbus units (1 unit ≈ 1A)')
    parser.add_argument('--voltage', type=int, default=DEFAULTS['voltage'],
                        help='Motor nominal voltage (10 = 1V)')
    parser.add_argument('--freq', type=int, default=DEFAULTS['frequency'],
                        help='Motor nominal frequency (10 = 1Hz)')
    parser.add_argument('--speed', type=int, default=DEFAULTS['speed'],
                        help='Motor nominal speed in RPM')
    parser.add_argument('--power', type=int, default=DEFAULTS['power'],
                        help='Motor nominal power (1 = 0.1kW)')
    parser.add_argument('--id-run', type=int, default=DEFAULTS['id_run_type'],
                        choices=[1, 2, 3], help='ID run type: 1=Normal, 2=Reduced, 3=Standstill')
    parser.add_argument('--skip-id-run', action='store_true',
                        help='Only set params, skip ID run')
    parser.add_argument('--skip-test', action='store_true',
                        help='Skip motor test after configuration')
    args = parser.parse_args()

    cfg = dict(DEFAULTS)
    cfg['current'] = args.current
    cfg['voltage'] = args.voltage
    cfg['frequency'] = args.freq
    cfg['speed'] = args.speed
    cfg['power'] = args.power
    cfg['id_run_type'] = args.id_run

    mc = MotorConfigurator()
    mc.connect()

    try:
        # 1. Set motor parameters
        if not mc.set_motor_params(cfg):
            print("\nERROR: Failed to set some parameters!")
            return

        # 2. Switch to vector control
        if not mc.set_vector_mode():
            print("\nERROR: Failed to set vector mode!")
            return

        # 3. ID run
        if not args.skip_id_run:
            if not mc.request_id_run(args.id_run):
                print("\nERROR: Failed to request ID run!")
                return

            if not mc.execute_id_run(timeout_sec=90):
                print("\nERROR: ID run failed or timed out!")
                if mc.check_faults():
                    print("Try resetting the fault and retrying.")
                return

        # 4. Save to NVM
        print("\n=== Saving to NVM ===")
        if mc.save_nvm():
            print("  Saved successfully!")
        else:
            print("  WARNING: NVM save may have failed")

        # 5. Verify
        mc.verify_config()

        # 6. Test motor
        if not args.skip_test:
            mc.test_motor(speed_pct=30, duration=5)

        print("\n=== Configuration Complete ===")

    finally:
        mc.close()


if __name__ == '__main__':
    main()
