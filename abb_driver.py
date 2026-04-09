"""
ABB ACS180 - Modbus RTU Driver
===============================
Two implementations:
  - RealABBDrive  : Communicates with real hardware via Modbus RTU
  - MockABBDrive  : Simulates a drive for testing without hardware

Both share the same interface (ABBDriveBase).
"""

import time
from abc import ABC, abstractmethod

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

import config


# ══════════════════════════════════════════════
# Base Interface
# ══════════════════════════════════════════════

class ABBDriveBase(ABC):
    """Abstract interface for ABB drive control."""

    @abstractmethod
    def connect(self) -> bool:
        """Open communication. Returns True on success."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close communication."""
        ...

    @abstractmethod
    def start(self) -> bool:
        """Send RUN command. Returns True on success."""
        ...

    @abstractmethod
    def stop(self) -> bool:
        """Send STOP command (ramp stop). Returns True on success."""
        ...

    @abstractmethod
    def set_speed(self, percent: float) -> bool:
        """
        Set speed reference.
        Args:
            percent: 0.0 – 100.0 (% of nominal speed)
        Returns True on success.
        """
        ...

    @abstractmethod
    def read_status(self) -> dict | None:
        """
        Read drive status.
        Returns dict with keys:
            status_word, running, fault, warning,
            ready, speed_percent, speed_rpm, current_a
        Or None on failure.
        """
        ...

    @abstractmethod
    def fault_reset(self) -> bool:
        """Reset a drive fault. Returns True on success."""
        ...

    @abstractmethod
    def emergency_stop(self) -> bool:
        """Emergency ramp stop. Returns True on success."""
        ...


# ══════════════════════════════════════════════
# Real Implementation (Modbus RTU)
# ══════════════════════════════════════════════

class RealABBDrive(ABBDriveBase):
    """Controls ABB ACS180 via Modbus RTU over RS485."""

    def __init__(
        self,
        port: str = config.COM_PORT,
        baudrate: int = config.BAUD_RATE,
        parity: str = config.PARITY,
        slave_id: int = config.SLAVE_ID,
        timeout: float = config.TIMEOUT,
    ):
        self.slave_id = slave_id
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=config.STOP_BITS,
            bytesize=config.BYTE_SIZE,
            timeout=timeout,
        )
        self._connected = False

    # ── Connection ─────────────────────────────

    def connect(self) -> bool:
        try:
            self._connected = self.client.connect()
            if self._connected:
                print(f"[OK] Connected to {self.client.comm_params.host} "
                      f"(Slave ID: {self.slave_id})")
            else:
                print("[ERROR] Could not open serial port.")
            return self._connected
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        if self._connected:
            self.client.close()
            self._connected = False
            print("[OK] Disconnected.")

    # ── Write helpers ──────────────────────────

    def _write_register(self, address: int, value: int) -> bool:
        """Write a single holding register. Returns True on success."""
        if not self._connected:
            print("[ERROR] Not connected.")
            return False
        try:
            result = self.client.write_register(
                address=address, value=value, device_id=self.slave_id
            )
            if result.isError():
                print(f"[ERROR] Write register {address} failed: {result}")
                return False
            return True
        except ModbusException as e:
            print(f"[ERROR] Modbus exception writing register {address}: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error writing register {address}: {e}")
            return False

    def _read_registers(self, address: int, count: int) -> list[int] | None:
        """Read holding registers. Returns list of values or None."""
        if not self._connected:
            print("[ERROR] Not connected.")
            return None
        try:
            result = self.client.read_holding_registers(
                address=address, count=count, device_id=self.slave_id
            )
            if result.isError():
                print(f"[ERROR] Read register {address} failed: {result}")
                return None
            return result.registers
        except ModbusException as e:
            print(f"[ERROR] Modbus exception reading register {address}: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error reading register {address}: {e}")
            return None

    # ── Drive Commands ─────────────────────────

    def start(self) -> bool:
        print("[CMD] Sending START...")
        # Step 1: Send STOP first to ensure clean state machine transition
        if not self._write_register(config.REG_CONTROL_WORD, config.CW_STOP):
            return False
        time.sleep(0.1)
        # Step 2: Send RUN
        ok = self._write_register(config.REG_CONTROL_WORD, config.CW_RUN)
        if ok:
            print("[OK] START command sent.")
        return ok

    def stop(self) -> bool:
        print("[CMD] Sending STOP (ramp)...")
        ok = self._write_register(config.REG_CONTROL_WORD, config.CW_STOP)
        if ok:
            print("[OK] STOP command sent.")
        return ok

    def emergency_stop(self) -> bool:
        print("[CMD] Sending EMERGENCY STOP...")
        ok = self._write_register(config.REG_CONTROL_WORD, config.CW_EMERGENCY)
        if ok:
            print("[OK] Emergency stop sent.")
        return ok

    def fault_reset(self) -> bool:
        print("[CMD] Resetting fault...")
        # Send fault reset (rising edge on bit 7)
        if not self._write_register(config.REG_CONTROL_WORD, config.CW_FAULT_RESET):
            return False
        time.sleep(0.3)
        # Return to stop state
        ok = self._write_register(config.REG_CONTROL_WORD, config.CW_STOP)
        if ok:
            print("[OK] Fault reset sent.")
        return ok

    def set_speed(self, percent: float) -> bool:
        if not (0.0 <= percent <= 100.0):
            print(f"[ERROR] Speed must be 0-100%, got {percent}")
            return False
        raw = int(percent * config.SPEED_REF_SCALE / 100.0)
        raw = max(0, min(config.SPEED_REF_SCALE, raw))
        print(f"[CMD] Setting speed to {percent:.1f}% (raw: {raw})")
        ok = self._write_register(config.REG_SPEED_REF, raw)
        if ok:
            print(f"[OK] Speed set to {percent:.1f}%")
        return ok

    def read_status(self) -> dict | None:
        # Read registers: status_word, actual_speed, actual_current
        regs = self._read_registers(config.REG_STATUS_WORD, 3)
        if regs is None or len(regs) < 1:
            return None

        status_word = regs[0]
        actual_speed_raw = regs[1] if len(regs) > 1 else 0
        actual_current_raw = regs[2] if len(regs) > 2 else 0

        speed_pct = actual_speed_raw * 100.0 / config.SPEED_REF_SCALE
        speed_rpm = speed_pct * config.MOTOR_NOM_RPM / 100.0
        current_a = actual_current_raw * 0.1  # ⚠️ Scale may differ – verify!

        return {
            "status_word": status_word,
            "status_hex": f"0x{status_word:04X}",
            "ready": bool(status_word & config.SW_READY_TO_SWITCH_ON),
            "ready_to_run": bool(status_word & config.SW_READY_TO_RUN),
            "running": bool(status_word & config.SW_RUNNING),
            "fault": bool(status_word & config.SW_FAULT),
            "warning": bool(status_word & config.SW_WARNING),
            "speed_percent": round(speed_pct, 2),
            "speed_rpm": round(speed_rpm, 1),
            "current_a": round(current_a, 2),
        }


# ══════════════════════════════════════════════
# Mock / Simulator Implementation
# ══════════════════════════════════════════════

class MockABBDrive(ABBDriveBase):
    """
    Simulates an ABB ACS180 drive for testing without hardware.
    Prints all actions to console and maintains internal state.
    """

    def __init__(self):
        self._connected = False
        self._running = False
        self._fault = False
        self._speed_pct = 0.0

    def connect(self) -> bool:
        self._connected = True
        print("[MOCK] Connected to simulated ABB ACS180.")
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._running = False
        print("[MOCK] Disconnected.")

    def start(self) -> bool:
        if self._fault:
            print("[MOCK] Cannot start – drive is in FAULT. Reset first.")
            return False
        self._running = True
        print(f"[MOCK] Drive STARTED at {self._speed_pct:.1f}%")
        return True

    def stop(self) -> bool:
        self._running = False
        print("[MOCK] Drive STOPPED (ramp).")
        return True

    def emergency_stop(self) -> bool:
        self._running = False
        print("[MOCK] EMERGENCY STOP!")
        return True

    def fault_reset(self) -> bool:
        self._fault = False
        self._running = False
        print("[MOCK] Fault reset. Drive ready.")
        return True

    def set_speed(self, percent: float) -> bool:
        if not (0.0 <= percent <= 100.0):
            print(f"[MOCK][ERROR] Speed must be 0-100%, got {percent}")
            return False
        self._speed_pct = percent
        rpm = percent * config.MOTOR_NOM_RPM / 100.0
        print(f"[MOCK] Speed set to {percent:.1f}% ({rpm:.0f} RPM)")
        return True

    def read_status(self) -> dict:
        speed_rpm = self._speed_pct * config.MOTOR_NOM_RPM / 100.0
        # Simulate current proportional to speed
        current = (self._speed_pct / 100.0) * 1.35 if self._running else 0.0

        status_word = 0
        if not self._fault:
            status_word |= config.SW_READY_TO_SWITCH_ON
            status_word |= config.SW_READY_TO_RUN
        if self._running:
            status_word |= config.SW_RUNNING
        if self._fault:
            status_word |= config.SW_FAULT

        return {
            "status_word": status_word,
            "status_hex": f"0x{status_word:04X}",
            "ready": not self._fault,
            "ready_to_run": not self._fault,
            "running": self._running,
            "fault": self._fault,
            "warning": False,
            "speed_percent": round(self._speed_pct, 2),
            "speed_rpm": round(speed_rpm, 1),
            "current_a": round(current, 2),
        }

    def simulate_fault(self):
        """Inject a simulated fault for testing."""
        self._fault = True
        self._running = False
        print("[MOCK] ⚡ Simulated FAULT injected!")
