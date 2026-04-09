# ABB ACS180 – Python Modbus RTU Control

שליטה ישירה על בקר ABB ACS180-04S-07A8 דרך Python באמצעות Modbus RTU (USB to RS485).

---

## 1. ארכיטקטורת המערכת

```
┌──────────┐    USB     ┌──────────────┐   RS485 (A/B)   ┌──────────────────┐   U/V/W   ┌─────────┐
│  מחשב    │ ────────── │ USB to RS485 │ ─────────────── │ ABB ACS180       │ ────────── │  מנוע   │
│ (Python) │            │  Converter   │                 │ 04S-07A8         │           │ Siemens │
└──────────┘            └──────────────┘                 │ 1ph→3ph 230V     │           │ 0.25kW  │
                                                         └──────────────────┘           └─────────┘
```

---

## 2. חיבורים פיזיים

### 2.1 חיבור מנוע לבקר (Delta Δ)

> **המנוע חייב להיות מחובר ב-Delta (Δ)** כי הבקר מוציא 3×230V.

```
ACS180 Output         Motor Terminal Block
─────────────         ────────────────────
   U (T1)  ──────────  U1
   V (T2)  ──────────  V1
   W (T3)  ──────────  W1

   חיבור Delta במנוע:
   ┌──────────────────────┐
   │  U1──W2  V1──U2  W1──V2  │
   │  (גשרים בין הטרמינלים)    │
   └──────────────────────┘
```

**חשוב:**
- ודא שהגשרים (jumpers) במנוע מחברים Delta: U1-W2, V1-U2, W1-V2
- חבר כבל הארקה (PE) מהבקר למנוע

### 2.2 חיבור RS485 (Modbus RTU)

הבקר ACS180 כולל ממשק RS485 מובנה בלוח ה-I/O:

```
USB-to-RS485 Converter        ACS180 I/O Terminals
──────────────────────        ────────────────────
    A (+)  ───────────────────  Terminal 21 (RS485 A+)
    B (-)  ───────────────────  Terminal 22 (RS485 B-)
    GND    ───────────────────  Terminal 24 (DGND)
```

> ⚠️ **הערה:** מספרי הטרמינלים (21/22/24) הם לפי התיעוד הסטנדרטי של ACS180.  
> **חובה לוודא מול המדריך שלך** – ראה תווית על הבקר או User Manual, פרק I/O Terminals.

### 2.3 Termination & Shielding

| נושא | המלצה |
|------|--------|
| Termination resistor (120Ω) | **כן** – אם הכבל ארוך מ-1 מטר, שים נגד 120Ω בין A ל-B בצד הממיר |
| Shield / שילד | חבר צד אחד לאדמה (GND) של הממיר |
| GND משותף | חבר GND של הממיר ל-DGND (Terminal 24) של הבקר |
| אורך כבל מקסימלי | עד 1200 מטר (תיאורטית), 10 מטר מספיק לשולחן |

---

## 3. הגדרות בבקר (Parameters)

### 3.1 מקור שליטה – Fieldbus

| Parameter | שם | ערך | הסבר |
|-----------|-----|------|-------|
| P10.01 | EXT1 Commands | **Fieldbus (EFB)** | מקור פקודת Start/Stop |
| P10.02 | EXT1 Ref1 Sel | **Fieldbus (EFB)** | מקור הפניית מהירות |

> 💡 בחלק מגרסאות ACS180 הפרמטר עשוי להיקרא "Command Source" ו-"Reference Source".  
> ערך "EFB" = Embedded Fieldbus = Modbus RTU מובנה.  
> **⚠️ PLACEHOLDER** – ודא את מספרי הפרמטרים המדויקים ב-Manual פרק "Operating Mode".

### 3.2 הגדרות Modbus RTU

| Parameter | שם | ערך מומלץ | הסבר |
|-----------|-----|-----------|-------|
| P58.01 | Station ID | **1** | כתובת Slave (1-247) |
| P58.02 | Baud Rate | **9600** | קצב תקשורת |
| P58.03 | Parity | **Even** | בדיקת זוגיות |

> **⚠️ PLACEHOLDER** – קבוצת פרמטרים 58 היא סטנדרטית ל-ACS180.  
> אם לא קיימת, חפש "Modbus" או "EFB" או "Communication" בתפריט הפרמטרים.

### 3.3 הגדרות נוספות קריטיות

| Parameter | שם | ערך | הסבר |
|-----------|-----|------|-------|
| P49.05 | Communication Loss Action | **Fault** או **Last Value** | מה קורה אם התקשורת נופלת |
| P49.06 | Communication Loss Timeout | **5.0 sec** | זמן עד שמזהים ניתוק |

> **⚠️ PLACEHOLDER** – מספרי הפרמטרים הללו דורשים אימות.  
> **חשוב מאוד** להגדיר פעולת ניתוק תקשורת לבטיחות!

---

## 4. פרמטרי מנוע

הגדרות אלה קריטיות לפעולה תקינה ולהגנה על המנוע:

| Parameter | שם | ערך | הסבר |
|-----------|-----|------|-------|
| P99.01 | Motor Nom Voltage | **230 V** | מתח נומינלי (Delta) |
| P99.02 | Motor Nom Current | **1.35 A** | זרם נומינלי (Delta) |
| P99.03 | Motor Nom Frequency | **50 Hz** | תדר נומינלי |
| P99.04 | Motor Nom Speed | **1350 rpm** | מהירות נומינלית |
| P99.05 | Motor Nom Power | **0.25 kW** | הספק נומינלי |

> **⚠️ PLACEHOLDER** – קבוצה 99 היא סטנדרטית לפרמטרי מנוע ב-ACS180.  
> ב-Drive Composer או בפאנל, חפש "Motor Data" או "Motor Nameplate".

### 4.1 Motor ID Run (אופציונלי אך מומלץ)

אחרי הזנת פרמטרי המנוע, הרץ **Motor ID Run** (זיהוי מנוע):
- הגדר P99.06 (Motor ID Run) = **Standstill ID** (ברוב המקרים)
- לחץ Start – הבקר ימדוד את פרמטרי המנוע אוטומטית
- זה ישפר את ביצועי הבקר משמעותית

---

## 5. הרצת הפרויקט

### התקנה
```bash
pip install pymodbus pyserial
```

### הרצה
```bash
# מצב סימולטור (בלי חומרה)
python main.py --sim

# מצב אמיתי
python main.py --port COM3
```

---

## 6. מבנה הפרויקט

```
ACS-180/
├── README.md           # המסמך הזה
├── requirements.txt    # תלויות Python
├── config.py          # הגדרות (COM, Slave ID, Registers)
├── abb_driver.py      # מנהל התקשורת (Real + Mock)
└── main.py            # תוכנית שליטה אינטראקטיבית
```

---

## 7. טבלת רגיסטרים (Modbus Holding Registers)

> **⚠️ כל הכתובות הן PLACEHOLDER / EXAMPLE**  
> חובה לאמת מול: **ABB ACS180 Firmware Manual → Modbus Register Map**

| Register | כתובת | סוג | תיאור | סקאלה |
|----------|--------|------|--------|--------|
| Control Word | 0 | Write | פקודת שליטה (Start/Stop/Reset) | Bitmask |
| Speed Reference | 1 | Write | הפניית מהירות | 0-10000 = 0-100.00% |
| Status Word | 2 | Read | סטטוס הבקר | Bitmask |
| Actual Speed | 3 | Read | מהירות בפועל | 0-10000 = 0-100.00% |
| Actual Current | 4 | Read | זרם בפועל | × 0.1A |

### Control Word (Bitmask) – ABB Standard Profile

| Bit | שם | 0 | 1 |
|-----|-----|---|---|
| 0 | ON / OFF1 | Stop (ramp) | Start |
| 1 | OFF2 | Coast stop | Normal |
| 2 | OFF3 | Emergency stop | Normal |
| 3 | Enable Operation | Disable | Enable |
| 4 | Ramp enable | - | Enable |
| 5 | Unfreeze ramp | - | Enable |
| 6 | Unfreeze setpoint | - | Enable |
| 7 | Fault reset | - | Reset (edge) |
| 10 | Control by PLC | - | Active |

**ערכים נפוצים:**
- `0x047F` = RUN (Start + all enables + PLC control)
- `0x047E` = STOP (ramp stop)
- `0x04FF` = FAULT RESET + RUN

### Status Word (Bitmask)

| Bit | שם | תיאור |
|-----|-----|--------|
| 0 | Ready to switch on | בקר מוכן |
| 1 | Ready to run | מוכן לריצה |
| 2 | Running | פועל |
| 3 | Fault | תקלה |
| 7 | Warning | אזהרה |

---

## 8. אימות רגיסטרים – מה לבדוק

1. **הורד את ה-Firmware Manual** של ACS180 מאתר ABB
2. חפש: "Modbus Register Map" או "Fieldbus Register Table"
3. אמת:
   - כתובת Control Word (צפוי: 0 או 1)
   - כתובת Status Word
   - כתובת Speed Reference
   - סקאלת המהירות (בד"כ 0-10000 = 0-100%)
4. אם יש הבדלים – עדכן את `config.py`

---

## 9. בטיחות

⚠️ **אזהרות חשובות:**
- **אל תעבוד על חיבורים כשהבקר מחובר לחשמל!**
- ודא שהמנוע מעוגן ולא יכול לזוז
- התחל תמיד במהירות נמוכה (10-20%)
- הגדר Communication Loss Action (ראה סעיף 3.3)
- שמור על גישה פיזית לניתוק חשמל (kill switch)
- **הבקר מכיל מתח מסוכן גם אחרי ניתוק – המתן 5 דקות!**
