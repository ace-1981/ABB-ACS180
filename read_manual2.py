"""Read ACS180 manual PDF and extract relevant sections - UTF-8 safe."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz
doc = fitz.open(r'C:\Users\Administrator\Desktop\VSCODE PROJECTS\ACS-180\EN_ACS180_FW_C_A5.pdf')
print(f'PDF has {len(doc)} pages')

out = open('manual_extract.txt', 'w', encoding='utf-8', errors='replace')

# Extract P21 pages
out.write("="*80 + "\nP21 REFERENCE SELECTION\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    if '21.03' in text or 'REF2 source' in text.lower() or ('21.0' in text and 'ref' in text.lower()):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:4000] + "\n")

# Modbus/fieldbus register map
out.write("\n" + "="*80 + "\nMODBUS/FIELDBUS REGISTERS\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    if 'register map' in text.lower() or ('modbus' in text.lower() and 'register' in text.lower()):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:4000] + "\n")

# Fieldbus reference / EFB
out.write("\n" + "="*80 + "\nFIELDBUS REFERENCE / EFB\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    if ('efb' in text.lower() or 'embedded fieldbus' in text.lower()) and ('ref' in text.lower()):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:4000] + "\n")

# P58 fieldbus config  
out.write("\n" + "="*80 + "\nP58 FIELDBUS CONFIG\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    if '58.0' in text and ('fieldbus' in text.lower() or 'comm' in text.lower()):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:4000] + "\n")

# Control through fieldbus
out.write("\n" + "="*80 + "\nCONTROL THROUGH FIELDBUS\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    tl = text.lower()
    if ('control through' in tl and 'fieldbus' in tl) or ('fieldbus control' in tl) or ('embedded fieldbus' in tl and 'control' in tl):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:5000] + "\n")

# Specifically look for "EFB" value in reference source options
out.write("\n" + "="*80 + "\nEFB / COMM ref options\n" + "="*80 + "\n")
for pn in range(len(doc)):
    text = doc[pn].get_text()
    if 'EFB' in text and ('source' in text.lower() or 'selection' in text.lower()):
        out.write(f"\n--- Page {pn+1} ---\n")
        out.write(text[:4000] + "\n")

out.close()
doc.close()
sz = os.path.getsize('manual_extract.txt')
print(f'Wrote manual_extract.txt ({sz} bytes)')
