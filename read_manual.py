"""Read ACS180 manual PDF and extract relevant sections."""
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pymupdf'], capture_output=True)

import fitz
doc = fitz.open(r'C:\Users\Administrator\Desktop\VSCODE PROJECTS\ACS-180\EN_ACS180_FW_C_A5.pdf')
print(f'PDF has {len(doc)} pages\n')

# Search for key pages
keywords = ['21.03', 'REF2 source', 'REF1 source', 'fieldbus', 'EFB', 'COMM',
            'speed reference', 'frequency reference', 'Modbus register',
            'register map', 'control word', 'reference word']

found_pages = set()
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    for kw in keywords:
        if kw.lower() in text.lower():
            found_pages.add(page_num)
            break

print(f"Found relevant content on {len(found_pages)} pages\n")

# Extract pages about P21
print("="*80)
print("SEARCHING FOR P21 (Reference selection) DETAILS")
print("="*80)
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    if '21.03' in text or 'REF2 source' in text.lower() or 'REF1 source' in text.lower():
        print(f"\n--- Page {page_num+1} ---")
        print(text[:3000])
        print("...")

# Extract pages about Modbus registers
print("\n" + "="*80)
print("SEARCHING FOR MODBUS REGISTER MAP")
print("="*80)
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    if 'register map' in text.lower() or 'modbus register' in text.lower() or 'fieldbus control' in text.lower():
        print(f"\n--- Page {page_num+1} ---")
        print(text[:3000])
        print("...")

# Extract pages about fieldbus speed reference
print("\n" + "="*80)
print("SEARCHING FOR FIELDBUS/EFB REFERENCE")
print("="*80)
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    if ('efb' in text.lower() or 'fieldbus' in text.lower()) and ('ref' in text.lower() or 'speed' in text.lower()):
        print(f"\n--- Page {page_num+1} ---")
        # Print more text for these crucial pages
        print(text[:4000])  
        print("...")

doc.close()
