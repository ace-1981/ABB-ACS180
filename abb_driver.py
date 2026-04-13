"""
ABB ACS180 - Modbus RTU Driver
===============================
Two implementations:
  - RealABBDrive  : Communicates with real hardware via Modbus RTU
  - MockABBDrive  : Simulates a drive for testing without hardware

Both share the same interface (ABBDriveBase).
"""

import threading
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
        self._last_ref = 0  # Track current reference value
        self._lock = threading.Lock()  # Serialize all Modbus access

    # ── Connection ─────────────────────────────

    def connect(self) -> bool:
        try:
            self._connected = self.client.connect()
            if self._connected:
                print(f"[OK] Connected to {self.client.comm_params.host} "
                      f"(Slave ID: {self.slave_id})")
                self._setup_efb_params()
            else:
                print("[ERROR] Could not open serial port.")
            return self._connected
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def _setup_efb_params(self):
        """Set EFB (Embedded Fieldbus) parameters required for Modbus control.
        Reads first, writes only if needed, then saves to NVM permanently."""
        params = [
            (20,  1, 14, "EXT1 commands = EFB"),
            (20,  6, 14, "EXT2 commands = EFB"),
            (22, 11,  8, "EXT1 speed ref1 = EFB"),
            (22, 18,  8, "EXT2 speed ref1 = EFB"),
            (28, 11,  8, "EXT1 freq ref1 = EFB"),
        ]
        print("[SETUP] Checking EFB parameters...")
        changed = False
        for group, index, value, desc in params:
            addr = config.param_addr(group, index)
            # Read current value first
            regs = self._read_registers(addr, 1)
            current = regs[0] if regs and len(regs) > 0 else None
            if current == value:
                print(f"  P{group:02d}.{index:02d} = {value} ({desc}) [OK already]")
                continue
            # Need to write
            ok = self._write_register(addr, value)
            print(f"  P{group:02d}.{index:02d} = {current} → {value} ({desc}) [{'OK' if ok else 'FAIL'}]")
            if ok:
                changed = True

        if changed:
            self._save_params_to_nvm()
        else:
            print("[SETUP] All EFB parameters already correct – no save needed.")

    def _save_params_to_nvm(self):
        """Save all parameter changes to permanent memory via P96.07."""
        print("[SETUP] Saving parameters to NVM (P96.07)...")
        ok = self._write_register(config.PARAM_SAVE_ADDR, config.PARAM_SAVE_VALUE)
        if ok:
            time.sleep(1)  # Give drive time to write to flash
            print("[OK] Parameters saved to permanent memory!")
        else:
            print("[ERROR] P96.07 save failed")

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
        with self._lock:
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

    def _write_registers(self, address: int, values: list[int]) -> bool:
        """Write multiple holding registers atomically (FC16)."""
        if not self._connected:
            print("[ERROR] Not connected.")
            return False
        with self._lock:
            try:
                result = self.client.write_registers(
                    address=address, values=values, device_id=self.slave_id
                )
                if result.isError():
                    print(f"[ERROR] Write registers {address} failed: {result}")
                    return False
                return True
            except ModbusException as e:
                print(f"[ERROR] Modbus exception writing registers {address}: {e}")
                return False
            except Exception as e:
                print(f"[ERROR] Unexpected error writing registers {address}: {e}")
                return False

    def _read_registers(self, address: int, count: int) -> list[int] | None:
        """Read holding registers. Returns list of values or None."""
        if not self._connected:
            print("[ERROR] Not connected.")
            return None
        with self._lock:
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

    def stop(self) -> bool:
        print("[CMD] Sending STOP (ramp)...")
        ok = self._write_registers(0, [config.CW_STOP, 0])
        if ok:
            self._last_ref = 0
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
        self._last_ref = raw
        ref = self._ref_with_direction(raw)
        print(f"[CMD] Setting speed to {percent:.1f}% (ref: {self._signed16(ref)})")
        ok = self._write_registers(0, [config.CW_RUN, ref])
        if ok:
            print(f"[OK] Speed set to {percent:.1f}%")
        return ok

    @staticmethod
    def _signed16(v: int) -> int:
        """Convert unsigned 16-bit to signed."""
        return v if v < 0x8000 else v - 0x10000

    def read_status(self) -> dict | None:
        # Read all 6 Data I/O registers at once (CW, Ref1, Ref2, SW, Act1, Act2)
        regs = self._read_registers(0, 6)
        if regs is None or len(regs) < 6:
            return None

        status_word = regs[3]
        act1_raw = self._signed16(regs[4])
        act2_raw = self._signed16(regs[5])

        # Act1 scaling: 0-20000 = 0-100% of nominal
        speed_pct = abs(act1_raw) * 100.0 / config.SPEED_REF_SCALE
        speed_rpm = speed_pct * config.MOTOR_NOM_RPM / 100.0
        freq_hz = speed_pct * config.MOTOR_NOM_FREQ / 100.0

        # Act2: current in 0.1 A units (verify with your drive)
        current_a = abs(act2_raw) * 0.1

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
            "frequency_hz": round(freq_hz, 1),
            "current_a": round(current_a, 2),
        }

    def read_params(self) -> dict:
        """Read key drive parameters for display."""
        param_list = [
            (1, 1, "Motor speed"),
            (1, 7, "Output frequency"),
            (1, 8, "Output current"),
            (1, 9, "Motor torque"),
            (1, 10, "Motor power"),
            (1, 11, "DC bus voltage"),
            (3, 9, "EFB ref1 actual"),
            (19, 12, "EXT1 ctrl mode"),
            (19, 14, "EXT2 ctrl mode"),
            (20, 1, "EXT1 commands"),
            (20, 6, "EXT2 commands"),
            (22, 11, "EXT1 speed ref1"),
            (22, 18, "EXT2 speed ref1"),
            (28, 11, "EXT1 freq ref1"),
            (46, 1, "Speed scaling"),
            (46, 2, "Freq scaling"),
            (58, 3, "Node address"),
            (58, 4, "Baud rate"),
        ]
        result = []
        for g, i, desc in param_list:
            addr = config.param_addr(g, i)
            regs = self._read_registers(addr, 1)
            val = self._signed16(regs[0]) if regs and len(regs) > 0 else None
            result.append({
                "param": f"P{g:02d}.{i:02d}",
                "value": val,
                "desc": desc,
            })
        return result

    def set_direction(self, reverse: bool) -> bool:
        """Set motor direction. Only call when motor is stopped!
        ACS180 uses signed reference: negative = reverse."""
        direction = "REVERSE" if reverse else "FORWARD"
        print(f"[CMD] Setting direction: {direction}")
        self._reverse = reverse
        print(f"[OK] Direction set to {direction}")
        return True

    def _ref_with_direction(self, raw: int) -> int:
        """Apply direction sign and convert to uint16 for Modbus."""
        signed_val = -raw if getattr(self, '_reverse', False) else raw
        return signed_val & 0xFFFF  # two's complement for uint16

    def start(self) -> bool:
        print("[CMD] Sending START...")
        if not self._write_register(config.REG_CONTROL_WORD, config.CW_STOP):
            return False
        time.sleep(0.1)
        ref = self._ref_with_direction(self._last_ref)
        ok = self._write_registers(0, [config.CW_RUN, ref])
        if ok:
            print(f"[OK] START sent (ref={self._signed16(ref)}).")
        return ok


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
            "frequency_hz": round(self._speed_pct * config.MOTOR_NOM_FREQ / 100.0, 1),
            "current_a": round(current, 2),
        }

    def simulate_fault(self):
        """Inject a simulated fault for testing."""
        self._fault = True
        self._running = False
        print("[MOCK] ⚡ Simulated FAULT injected!")

    def read_params(self) -> list:
        return [{"param": "P01.01", "value": 0, "desc": "Mock param"}]

    def set_direction(self, reverse: bool) -> bool:
        self._reverse = reverse
        print(f"[MOCK] Direction: {'REVERSE' if reverse else 'FORWARD'}")
        return True
