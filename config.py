"""
ABB ACS180 - Configuration File
================================
All configurable parameters in one place.
Update these values to match your setup.
"""

# ──────────────────────────────────────────────
# Serial / Communication Settings
# ──────────────────────────────────────────────
COM_PORT = "COM4"           # Change to your USB-to-RS485 port
BAUD_RATE = 19200           # Must match P58.04 on the drive (19.2 kbps)
PARITY = "E"                # "E"=Even, "O"=Odd, "N"=None – must match P58.05
STOP_BITS = 1
BYTE_SIZE = 8
SLAVE_ID = 1                # Must match P58.03 on the drive (node address)
TIMEOUT = 1.0               # Serial timeout in seconds

# ──────────────────────────────────────────────
# Modbus Register Addresses (Holding Registers)
# ──────────────────────────────────────────────
# ⚠️  PLACEHOLDER / EXAMPLE VALUES
# You MUST verify these against the ACS180 Firmware Manual
# Look for: "Modbus Register Map" or "Fieldbus Registers"
#
# Data I/O registers (confirmed via P58.101–P58.106)
REG_CONTROL_WORD = 0        # CW  – Control Word (write)
REG_SPEED_REF    = 1        # Ref1 – Speed / Frequency reference (write), 0‥20000
REG_REF2         = 2        # Ref2 – Secondary reference (write)
REG_STATUS_WORD  = 3        # SW  – Status Word (read)
REG_ACTUAL_1     = 4        # Act1 – Actual value 1 (read) – speed / freq
REG_ACTUAL_2     = 5        # Act2 – Actual value 2 (read) – current

# ──────────────────────────────────────────────
# Control Word Values (ABB Standard Profile)
# ──────────────────────────────────────────────
# Bits: 10=PLC ctrl, 6=unfreeze setpoint, 5=unfreeze ramp,
#       4=ramp enable, 3=enable op, 2=OFF3, 1=OFF2, 0=ON
#
CW_STOP        = 0x047E     # All enables ON, bit0=0 → ramp stop
CW_RUN         = 0x047F     # All enables ON, bit0=1 → run
CW_FAULT_RESET = 0x04FF     # Bit 7=1 → reset fault (then send CW_RUN)
CW_COAST_STOP  = 0x047C     # Bit 1=0 → coast stop (no ramp)
CW_EMERGENCY   = 0x047B     # Bit 2=0 → emergency ramp stop

# ──────────────────────────────────────────────
# Status Word Bit Masks
# ──────────────────────────────────────────────
SW_READY_TO_SWITCH_ON = 0x0001   # Bit 0
SW_READY_TO_RUN       = 0x0002   # Bit 1
SW_RUNNING            = 0x0004   # Bit 2
SW_FAULT              = 0x0008   # Bit 3
SW_OFF2_ACTIVE        = 0x0010   # Bit 4
SW_OFF3_ACTIVE        = 0x0020   # Bit 5
SW_SWITCH_ON_INHIBIT  = 0x0040   # Bit 6
SW_WARNING            = 0x0080   # Bit 7

# ──────────────────────────────────────────────
# Motor / Speed Settings
# ──────────────────────────────────────────────
MOTOR_NOM_RPM  = 1350       # Nominal motor speed (rpm)
MOTOR_NOM_FREQ = 50         # Nominal frequency (Hz)
SPEED_REF_MAX  = 20000      # Full scale reference
SPEED_REF_SCALE = 20000     # 20000 = 100 % of nominal

# Scaling factors (from P46.01 / P46.02 on drive)
SCALE_SPEED = 500           # P46.01 – 20000 → 500 rpm
SCALE_FREQ  = 1000          # P46.02 – 20000 → 100.0 Hz

# Address helper: PDU = group*100 + index − 1
def param_addr(group: int, index: int) -> int:
    return group * 100 + index - 1

# P96.07 – "Parameter save manually": saves fieldbus changes to NVM
PARAM_SAVE_ADDR = param_addr(96, 7)   # = 9606
PARAM_SAVE_VALUE = 1                   # 1 = Save (reverts to 0 = Done)
