# ABB ACS180 – מסמך סיכום: חיבור, תקלות, פתרונות ומסקנות

**תאריך:** 9 באפריל 2026  
**בקר:** ABB ACS180-04S-07A8 (1ph→3ph, 230V)  
**מנוע:** Siemens 0.25kW, 1350 RPM  
**תקשורת:** Modbus RTU מעל RS485  

---

## תוכן עניינים
1. [ארכיטקטורת המערכת](#1-ארכיטקטורת-המערכת)
2. [חיבורים פיזיים](#2-חיבורים-פיזיים)
3. [הגדרות בבקר (Parameters)](#3-הגדרות-בבקר)
4. [הגדרות תוכנה (config.py)](#4-הגדרות-תוכנה)
5. [בעיות שנתקלנו בהן ואיך פתרנו](#5-בעיות-שנתקלנו-בהן-ואיך-פתרנו)
6. [מסקנות ולקחים לחיבור הבקר הבא](#6-מסקנות-ולקחים-לחיבור-הבא)
7. [צ'קליסט מלא לחיבור בקר חדש](#7-צקליסט-מלא)

---

## 1. ארכיטקטורת המערכת

```
┌──────────┐    USB     ┌──────────────┐   RS485 (A/B)   ┌──────────────────┐   U/V/W   ┌─────────┐
│  מחשב    │ ────────── │ USB to RS485 │ ─────────────── │ ABB ACS180       │ ────────── │  מנוע   │
│ (Python) │            │  Converter   │                 │ 04S-07A8         │           │ Siemens │
└──────────┘            └──────────────┘                 │ 1ph→3ph 230V     │           │ 0.25kW  │
                                                         └──────────────────┘           └─────────┘
```

**ספריות Python:** `pymodbus`, `pyserial`, `flask` (לדשבורד ווב)

---

## 2. חיבורים פיזיים

### 2.1 חיבור RS485 (Modbus RTU)

| ממיר USB-to-RS485 | טרמינל בבקר ACS180 | הערה |
|---|---|---|
| **A (+)** | **Terminal 21 (RS485 A+)** | חוט חיובי |
| **B (-)** | **Terminal 22 (RS485 B-)** | חוט שלילי |
| **GND** | **Terminal 24 (DGND)** | אדמה דיגיטלית – **קריטי!** |

> ⚠️ **חובה לוודא** את מספרי הטרמינלים מול התווית על הבקר או ה-User Manual (פרק I/O Terminals).

#### Termination & Shielding

| פרמטר | ערך | הערה |
|---|---|---|
| נגד סיום (Termination) | **120Ω בין A ל-B** | בצד הממיר, אם הכבל ארוך מ-1 מטר |
| Shield / שילד | צד אחד ל-GND של הממיר | |
| GND משותף | **חובה** – GND ממיר ↔ DGND בבקר (Terminal 24) | |
| אורך כבל מקסימלי | עד 1200 מטר (תיאורטית) | |

### 2.2 חיבור מנוע (Delta Δ – 230V)

המנוע **חייב** להיות ב-Delta כי הבקר מוציא 3×230V:

```
ACS180 Output         Motor Terminal Block
─────────────         ────────────────────
   U (T1)  ──────────  U1
   V (T2)  ──────────  V1
   W (T3)  ──────────  W1

   גשרים Delta במנוע: U1-W2, V1-U2, W1-V2
```

- חבר כבל הארקה (PE) מהבקר למנוע

---

## 3. הגדרות בבקר (Parameters)

### 3.1 הגדרות Modbus RTU – קבוצה 58

| פרמטר | שם | ערך שהוגדר | הערות |
|---|---|---|---|
| **P58.01** | Protocol Selection | **Modbus RTU** | הפעלת תקשורת מובנית |
| **P58.03** | Node Address / Station ID | **1** | כתובת Slave (1-247) |
| **P58.04** | Baud Rate | **19200** | ערכים אפשריים: [1]4800, [2]9600, [3]19200, [4]38400, [5]57600, [6]76800, [7]115200 |
| **P58.05** | Parity | **8E1 (Even)** | ערכים: [0]8N1, [1]8N2, [2]8E1, [3]8O1 |
| **P58.06** | ⚡ **Refresh Settings** | **ביצוע** | **קריטי!** חובה לבצע אחרי כל שינוי בהגדרות תקשורת |

### 3.2 מקור שליטה – Fieldbus

| פרמטר | שם | ערך | הערה |
|---|---|---|---|
| **P10.01** | EXT1 Commands | **Fieldbus (EFB)** | מקור פקודת Start/Stop |
| **P10.02** | EXT1 Ref1 Sel | **Fieldbus (EFB)** | מקור הפניית מהירות |

> ⚠️ EFB = Embedded Fieldbus = Modbus RTU מובנה. יכול להופיע גם כ-"Command Source" ו-"Reference Source".

### 3.3 הגדרות בטיחות – Communication Loss

| פרמטר | שם | ערך מומלץ | הערה |
|---|---|---|---|
| **P49.05** | Communication Loss Action | **Fault** או **Last Value** | מה קורה כשהתקשורת נופלת |
| **P49.06** | Communication Loss Timeout | **5.0 sec** | זמן עד שמזהים ניתוק |

### 3.4 פרמטרי מנוע – קבוצה 99

| פרמטר | שם | ערך | הערה |
|---|---|---|---|
| P99.01 | Motor Nom Voltage | **230 V** | מתח נומינלי (Delta) |
| P99.02 | Motor Nom Current | **1.35 A** | זרם נומינלי (Delta) |
| P99.03 | Motor Nom Frequency | **50 Hz** | תדר נומינלי |
| P99.04 | Motor Nom Speed | **1350 rpm** | מהירות נומינלית |
| P99.05 | Motor Nom Power | **0.25 kW** | הספק נומינלי |

> 💡 **Motor ID Run** (P99.06 = Standstill ID) – אופציונלי אך מומלץ מאוד. הבקר מודד את פרמטרי המנוע אוטומטית ומשפר ביצועים.

---

## 4. הגדרות תוכנה (config.py)

### 4.1 הגדרות Serial

```python
COM_PORT   = "COM4"     # פורט USB-to-RS485
BAUD_RATE  = 19200      # חייב להתאים ל-P58.04
PARITY     = "E"        # "E"=Even – חייב להתאים ל-P58.05
STOP_BITS  = 1
BYTE_SIZE  = 8
SLAVE_ID   = 1          # חייב להתאים ל-P58.03
TIMEOUT    = 1.0        # שניות
```

### 4.2 כתובות רגיסטרים (Modbus Holding Registers)

| רגיסטר | כתובת | סוג | תיאור | סקאלה |
|---|---|---|---|---|
| **Control Word** | 0 | Write | פקודת שליטה (Start/Stop/Reset) | Bitmask |
| **Speed Reference** | 1 | Write | הפניית מהירות/תדר | 0-20000 = 0-50Hz |
| **Status Word** | 3 | Read | סטטוס הבקר | Bitmask |
| **Actual Speed** | 3 | Read | מהירות בפועל | 0-20000 = 0-50Hz |
| **Actual Current** | 4 | Read | זרם בפועל | ×0.1A |

> ⚠️ חובה לאמת כתובות מול ABB ACS180 Firmware Manual → Modbus Register Map

### 4.3 ערכי Control Word

| שם | ערך | ביטים | פעולה |
|---|---|---|---|
| **CW_STOP** | `0x047E` | All enables ON, bit0=0 | עצירה מבוקרת (ramp) |
| **CW_RUN** | `0x047F` | All enables ON, bit0=1 | הפעלה |
| **CW_FAULT_RESET** | `0x04FF` | bit7=1 | איפוס תקלה (rising edge) |
| **CW_COAST_STOP** | `0x047C` | bit1=0 | עצירה חופשית |
| **CW_EMERGENCY** | `0x047B` | bit2=0 | עצירת חירום |

**מבנה Control Word (ABB Standard Profile):**
| ביט | תפקיד | 0 | 1 |
|---|---|---|---|
| 0 | ON/OFF1 | Stop (ramp) | Start |
| 1 | OFF2 | Coast stop | Normal |
| 2 | OFF3 | Emergency stop | Normal |
| 3 | Enable Operation | Disable | Enable |
| 4 | Ramp enable | - | Enable |
| 5 | Unfreeze ramp | - | Enable |
| 6 | Unfreeze setpoint | - | Enable |
| 7 | Fault reset | - | Reset (edge) |
| 10 | Control by PLC | - | Active |

### 4.4 ביטי Status Word

| ביט | שם | משמעות |
|---|---|---|
| 0 | Ready to switch on | בקר מוכן |
| 1 | Switched on / Ready to run | מוכן לריצה |
| 2 | Operation enabled / Running | פועל |
| 3 | Fault | תקלה פעילה |
| 4 | Voltage enabled | מתח מופעל |
| 5 | Quick stop | עצירה מהירה |
| 6 | Switch on disabled | הפעלה מנוטרלת |
| 7 | Warning | אזהרה |

> 💡 **Status Word = 0** → הבקר מתעלם מ-Modbus! צריך להפעיל Remote mode ולהגדיר Fieldbus כמקור שליטה.

### 4.5 סקאלת מהירות

```python
SPEED_REF_SCALE = 20000    # 20000 = 50Hz (0-20000 = 0-50Hz)
MOTOR_NOM_RPM   = 1350     # RPM נומינלי
```

**חישוב:**
- אחוז = `raw_value × 100 / 20000`
- RPM = `percent × 1350 / 100`
- כתיבה: `raw = int(percent × 20000 / 100)`

---

## 5. בעיות שנתקלנו בהן ואיך פתרנו

### 🔴 בעיה 1: אין תגובה מהבקר בכלל

**תסמינים:** שליחת Modbus frames – אפס תגובה מהבקר.

**מה ניסינו:**
1. `comm_test.py` – בדיקה שיטתית של כל קצבי שידור (9600, 19200, 38400…) וכל סוגי Parity
2. `scan.py` – סריקה עמוקה של כל שילובי baud × parity × slave ID × register
3. `diagnose.py` – 5 שלבי אבחון: פתיחת פורט, loopback, כל ה-combos, function codes שונים, בדיקת חומרה
4. `test_all_combos.py` – כל השילובים מתוך המדריך של ACS180

**פתרון:**
- ✅ **P58.06 – Refresh Settings**: הגדרות התקשורת לא נכנסו לתוקף עד שביצענו Refresh!
- ✅ **Power cycle**: כיבוי-הדלקה של הבקר אחרי שינוי הגדרות תקשורת
- ✅ ודאנו ש-P58.01 = Modbus RTU (ולא Disabled)

### 🔴 בעיה 2: Echo מזויף מהממיר (KA301)

**תסמינים:** קיבלנו בחזרה בית `0x00` או echo של מה ששלחנו – נראה כמו תגובה אבל אינו תגובה אמיתית.

**מה ניסינו:**
1. `echo_test.py` – שליחת frames שונים ובדיקה אם התגובה משתנה בהתאם
2. `aggressive_test.py` – שליחת 0xAA ובדיקה אם חוזר 0xAA (echo) 
3. **Silence test** – המתנה בלי לשלוח כלום ובדיקה אם מגיעים bytes (=רעש קו)

**ממצאים:**
- הממיר KA301 מחזיר echo של TX חזרה ל-RX
- `0x00` שקיבלנו היה רעש על הקו ולא תגובה אמיתית

**פתרון:**
- ✅ זיהוי שה-echo הוא מהממיר ולא מהבקר
- ✅ תגובה אמיתית היא ≥5 bytes עם slave ID תואם ו-function code תקין
- ✅ אם מקבלים echo: בדוק אם חיווט TX מתחבר ל-RX בממיר

### 🔴 בעיה 3: חיווט A/B הפוך

**תסמינים:** הממיר עובד (loopback תקין), אך אין תגובה מהבקר.

**מה ניסינו:**
1. `loopback_test.py` – קיצור A ו-B יחד וודאנו שהממיר שולח ומקבל
2. `test_wiring.py` – סקריפט שרץ בלולאה כל 2 שניות – מזהה מיד כשהתקשורת עולה
3. `quick_raw_test.py` – בדיקה מהירה אחרי החלפת חוטים

**פתרון:**
- ✅ **החלפת A ו-B** – חיבור A+ של הממיר ל-A+ של הבקר (ולא בהיפוך)
- ✅ שימוש ב-`test_wiring.py` לאימות בזמן אמת תוך כדי החלפת חוטים פיזית

### 🔴 בעיה 4: קצב שידור לא תואם

**תסמינים:** הממיר שולח, אין תגובה מהבקר (או תגובה משובשת).

**מה ניסינו:**
- `comm_test.py` – raw Modbus test בכל הקצבים: 4800, 9600, 19200, 38400, 57600, 115200
- `test_all_combos.py` – כל השילובים מהמדריך

**פתרון:**
- ✅ וידאנו ש-**P58.04 בבקר = 19200** (ערך [3])
- ✅ וידאנו ש-**P58.05 בבקר = 8E1** (ערך [2]) – Even Parity
- ✅ התאמנו ב-`config.py`: `BAUD_RATE = 19200`, `PARITY = "E"`

### 🔴 בעיה 5: Status Word = 0 (בקר לא נשלט דרך Modbus)

**תסמינים:** תקשורת עובדת (קריאות חוזרות עם ערכים), אבל Status Word = 0 ופקודות RUN לא עובדות.

**מה ניסינו:**
1. `debug_regs3.py` – ניתוח מעמיק של Status Word
2. `live_monitor.py` – מעקב בזמן אמת אחרי Status Word תוך שינוי הגדרות בפאנל

**ממצאים:**
- Status Word = 0 אומר: **הבקר מתעלם לחלוטין מ-Modbus**
- הבקר צריך להיות במצב REMOTE ומקור השליטה חייב להיות Fieldbus

**פתרון:**
- ✅ לחיצת **LOC/REM** בפאנל הבקר → מעבר למצב REMOTE
- ✅ הגדרת **P10.01 = Fieldbus (EFB)** – מקור פקודות Start/Stop
- ✅ הגדרת **P10.02 = Fieldbus (EFB)** – מקור הפניית מהירות
- ✅ שימוש ב-`live_monitor.py` לראות בזמן אמת מתי Status Word משתנה מ-0

### 🔴 בעיה 6: כתיבת Speed Reference לא נשמרת

**תסמינים:** כותבים ערך 5000 לרגיסטר 1, קוראים בחזרה וזה 0 (הבקר דורס).

**מה ניסינו:**
1. `debug_regs.py` – Write test של CW_RUN לרגיסטר 0
2. `debug_regs2.py` – Write + readback test לרגיסטר 1
3. `debug_regs3.py` – Write test מפורט עם אימות

**פתרון:**
- ✅ הבקר דורס ערכים כשהוא לא במצב Fieldbus control
- ✅ אחרי הגדרת P10.01 ו-P10.02 ל-Fieldbus → כתיבות נשמרות
- ✅ רצף הפעלה נכון: קודם STOP, המתנה, אח"כ RUN

### 🔴 בעיה 7: תקלה 6681 (Communication Loss)

**תסמינים:** הבקר נכנס לתקלה 6681 כשאין תקשורת פעילה.

**פתרון:**
- ✅ פעולת Fault Reset בפאנל הבקר
- ✅ **מיד** אחרי Reset – להריץ את סקריפט הבדיקה (לפני שה-timeout גורם לתקלה חוזרת)
- ✅ הגדרת P49.06 (Timeout) לערך מספיק גבוה בזמן Development
- ✅ שימוש ב-`fault_reset()` בקוד לפני פקודת START

### 🔴 בעיה 8: בעיות עם ממיר USB-to-RS485

**תסמינים:** הממיר לא מזוהה, TX/RX LED לא מהבהבים, אין תקשורת.

**מה ניסינו:**
1. `ftdi_diag.py` – בדיקת FTDI: RTS/DTR control, RS485 mode flag, VID/PID
2. `final_test.py` – סריקת כל פורטי COM אחרי ניתוק-חיבור USB
3. `loopback_test.py` – אימות שהממיר עצמו עובד

**פתרון:**
- ✅ ניתוק וחיבור מחדש של כבל USB (כולל בדיקת Device Manager)
- ✅ בדיקת TX LED – אם לא מהבהב, הממיר לא שולח
- ✅ loopback test (קיצור A-B) לאימות
- ✅ ניסיון עם RTS/DTR שונים (חלק מהממירים משתמשים ב-RTS להפעלת TX)

---

## 6. מסקנות ולקחים לחיבור הבקר הבא

### 📋 סדר פעולות נכון לחיבור בקר ABB חדש

1. **חיווט פיזי** – חבר A→A, B→B, GND→DGND. שים נגד 120Ω אם כבל ארוך.
2. **הגדרות תקשורת בפאנל** – P58.01=Modbus RTU, P58.03=1, P58.04=19200, P58.05=8E1
3. **⚡ P58.06 – REFRESH!** – אחרי כל שינוי בקבוצה 58
4. **Power Cycle** – כבה והדלק את הבקר
5. **בדוק loopback** – קצר A-B בממיר, הרץ `loopback_test.py`
6. **הרץ `comm_test.py`** – ודא שהבקר מגיב
7. **הגדר Fieldbus** – P10.01=EFB, P10.02=EFB, LOC/REM→REMOTE
8. **הזן פרמטרי מנוע** – P99.01-P99.05
9. **התחל בנמוך** – מהירות 10-20% בלבד
10. **הרץ Motor ID Run** – P99.06 לאופטימיזציה

### ⚡ לקחים קריטיים

| לקח | הסבר |
|---|---|
| **P58.06 חובה** | שינוי פרמטרי תקשורת לא נכנס לתוקף בלי Refresh / Power Cycle |
| **LOC/REM** | הבקר חייב להיות ב-REMOTE כדי לקבל פקודות Modbus |
| **Status Word = 0 = בעיה** | אם SW=0, הבקר מתעלם – בדקו P10.01/P10.02 |
| **A/B יכולים להיות הפוכים** | אם אין תגובה – נסו להחליף A ו-B |
| **Echo ≠ תגובה** | echo מהממיר (0x00 או frame שלם בחזרה) הוא לא תגובה מהבקר |
| **תגובה אמיתית ≥ 5 bytes** | slave ID + function code + data + CRC |
| **STOP לפני RUN** | רצף Control Word: שלח STOP ← המתן 100-300ms ← שלח RUN |
| **Fault Reset = rising edge** | שלח CW_FAULT_RESET, המתן 300ms, חזור ל-CW_STOP |
| **Timeout בזמן פיתוח** | הגדל P49.06 כדי למנוע תקלות 6681 חוזרות |

### 🔧 כלי דיבוג מומלצים (לפי סדר שימוש)

| סקריפט | מתי להשתמש |
|---|---|
| `loopback_test.py` | ראשית – ודא שהממיר עובד |
| `comm_test.py` | שלב 2 – בדוק אם הבקר מגיב |
| `test_wiring.py` | אם אין תגובה – החלף חוטים בזמן אמת |
| `test_all_combos.py` | אם לא בטוחים מה ה-baud/parity בבקר |
| `live_monitor.py` | מעקב אחרי שינויים בפאנל |
| `debug_regs3.py` | ניתוח Status Word וזיהוי בעיית command source |
| `scan_regs.py` | זיהוי רגיסטרים פעילים תוך כדי ריצה |
| `run_motor_test.py` | בדיקת הפעלת מנוע (START 10% → 10 שניות → STOP) |

---

## 7. צ'קליסט מלא לחיבור בקר חדש

### שלב א': חומרה
- [ ] ממיר USB-to-RS485 מחובר למחשב (בדוק Device Manager → COM port)
- [ ] חוט A+ ממיר → Terminal 21 (A+) בבקר
- [ ] חוט B- ממיר → Terminal 22 (B-) בבקר
- [ ] חוט GND ממיר → Terminal 24 (DGND) בבקר
- [ ] נגד 120Ω בין A ל-B (אם כבל > 1 מטר)
- [ ] מנוע מחובר Delta (U1-W2, V1-U2, W1-V2)
- [ ] כבל הארקה PE מחובר

### שלב ב': הגדרות בקר – תקשורת
- [ ] P58.01 = Modbus RTU (Enabled)
- [ ] P58.03 = 1 (Node Address)
- [ ] P58.04 = 19200 (Baud Rate) – ערך [3]
- [ ] P58.05 = 8E1 (Parity) – ערך [2]
- [ ] **⚡ P58.06 = Refresh Settings – ביצוע!**
- [ ] **Power Cycle – כיבוי והדלקה**

### שלב ג': הגדרות בקר – שליטה
- [ ] P10.01 = Fieldbus (EFB) – מקור פקודות
- [ ] P10.02 = Fieldbus (EFB) – מקור מהירות
- [ ] LOC/REM → **REMOTE**
- [ ] P49.05 = Fault (Communication Loss Action)
- [ ] P49.06 = 10 sec (Communication Loss Timeout – ערך גבוה לפיתוח)

### שלב ד': פרמטרי מנוע
- [ ] P99.01 = מתח נומינלי (מהלוחית של המנוע)
- [ ] P99.02 = זרם נומינלי (מהלוחית, ערך Delta)
- [ ] P99.03 = תדר נומינלי (50 Hz)
- [ ] P99.04 = מהירות נומינלית RPM
- [ ] P99.05 = הספק נומינלי kW
- [ ] (אופציונלי) P99.06 = Motor ID Run → Standstill ID

### שלב ה': אימות תוכנה
- [ ] עדכן `config.py` – COM_PORT, BAUD_RATE, PARITY, SLAVE_ID
- [ ] הרץ `loopback_test.py` – ממיר עובד?
- [ ] הרץ `comm_test.py` – בקר מגיב?
- [ ] הרץ `quick_test.py` – קריאת רגיסטרים?
- [ ] Status Word ≠ 0 ? (אם 0 → חזור לשלב ג')
- [ ] הרץ `run_motor_test.py` – מנוע מסתובב?
- [ ] הרץ `web_app.py --real` – דשבורד עובד?

### שלב ו': בטיחות
- [ ] אל תעבוד על חיבורים כשהבקר מחובר לחשמל!
- [ ] המנוע מעוגן ולא יכול לזוז
- [ ] התחל תמיד במהירות נמוכה (10-20%)
- [ ] גישה פיזית לניתוק חשמל (kill switch)
- [ ] הבקר מכיל מתח מסוכן גם אחרי ניתוק – **המתן 5 דקות**

---

## סיכום קצר

**ההגדרה שעבדה בסוף:**
```
COM_PORT  = COM4
BAUD_RATE = 19200
PARITY    = Even (8E1)
SLAVE_ID  = 1
STOP_BITS = 1
BYTE_SIZE = 8

Control Word  → Register 0  (write)
Speed Ref     → Register 1  (write, 0-20000 = 0-50Hz)
Status Word   → Register 3  (read)
Actual Current→ Register 4  (read, ×0.1A)

CW_RUN  = 0x047F
CW_STOP = 0x047E
```

**3 הבעיות הכי נפוצות:**
1. שכחנו P58.06 Refresh → בקר לא מגיב
2. A/B הפוכים → בקר לא מגיב
3. לא הגדרנו Fieldbus כמקור שליטה → Status Word = 0
