"""
ABB ACS180 – Interactive Control via Python
=============================================
Usage:
    python main.py --sim          # Simulator mode (no hardware)
    python main.py --port COM3    # Real drive on COM3
    python main.py                # Real drive on default port (config.py)
"""

import argparse
import sys

from abb_driver import RealABBDrive, MockABBDrive, ABBDriveBase
import config


def print_status(status: dict | None) -> None:
    """Pretty-print drive status."""
    if status is None:
        print("  [ERROR] Could not read status.")
        return

    print("\n  ┌─────────────────────────────────┐")
    print(f"  │ Status Word:  {status['status_hex']:>16s} │")
    print(f"  │ Ready:        {'YES' if status['ready'] else 'NO':>16s} │")
    print(f"  │ Running:      {'YES' if status['running'] else 'NO':>16s} │")
    print(f"  │ Fault:        {'YES' if status['fault'] else 'NO':>16s} │")
    print(f"  │ Warning:      {'YES' if status['warning'] else 'NO':>16s} │")
    print(f"  │ Speed:     {status['speed_percent']:>7.1f}% / {status['speed_rpm']:>6.0f} RPM │")
    print(f"  │ Current:        {status['current_a']:>8.2f} A │")
    print("  └─────────────────────────────────┘\n")


def print_menu() -> None:
    print("=" * 42)
    print("  ABB ACS180 Control Menu")
    print("=" * 42)
    print("  1. Start")
    print("  2. Stop")
    print("  3. Set Speed (%)")
    print("  4. Read Status")
    print("  5. Fault Reset")
    print("  6. Emergency Stop")
    if hasattr(drive, 'simulate_fault'):
        print("  7. Simulate Fault (mock only)")
    print("  0. Exit")
    print("-" * 42)


def run_interactive(drive: ABBDriveBase) -> None:
    """Main interactive loop."""
    print("\nConnecting to drive...")
    if not drive.connect():
        print("Failed to connect. Exiting.")
        sys.exit(1)

    try:
        while True:
            print_menu()
            choice = input("  > ").strip()

            if choice == "1":
                drive.start()

            elif choice == "2":
                drive.stop()

            elif choice == "3":
                try:
                    pct = float(input("  Speed (0-100%): ").strip())
                    drive.set_speed(pct)
                except ValueError:
                    print("  [ERROR] Invalid number.")

            elif choice == "4":
                status = drive.read_status()
                print_status(status)

            elif choice == "5":
                drive.fault_reset()

            elif choice == "6":
                confirm = input("  Confirm emergency stop? (y/n): ").strip().lower()
                if confirm == "y":
                    drive.emergency_stop()

            elif choice == "7" and hasattr(drive, 'simulate_fault'):
                drive.simulate_fault()

            elif choice == "0":
                print("\nStopping drive before exit...")
                drive.stop()
                break

            else:
                print("  Invalid choice.")

    except KeyboardInterrupt:
        print("\n\n[!] Ctrl+C – stopping drive...")
        drive.stop()

    finally:
        drive.disconnect()
        print("Bye.")


# ══════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ABB ACS180 Python Controller")
    parser.add_argument("--sim", action="store_true", help="Use simulator (no hardware)")
    parser.add_argument("--port", type=str, default=None, help="Serial port (e.g. COM3)")
    parser.add_argument("--slave", type=int, default=None, help="Modbus slave ID")
    parser.add_argument("--baud", type=int, default=None, help="Baud rate")
    args = parser.parse_args()

    if args.sim:
        print(">>> SIMULATOR MODE <<<")
        drive = MockABBDrive()
    else:
        port = args.port or config.COM_PORT
        slave = args.slave or config.SLAVE_ID
        baud = args.baud or config.BAUD_RATE
        print(f">>> REAL MODE: {port}, Slave={slave}, Baud={baud} <<<")
        drive = RealABBDrive(port=port, slave_id=slave, baudrate=baud)

    run_interactive(drive)
