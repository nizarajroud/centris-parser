#!/usr/bin/env python3

import os
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

def fix_walkscore_display():
    """Fix walkscore display issues by analyzing and reporting the current state"""
    
    excel_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    print(f"📊 Analyzing {excel_file}...")
    
    wb = load_workbook(excel_file)
    ws = wb.active
    
    # Find columns
    walkscore_col = None
    address_col = None
    
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header == "WalkScore":
            walkscore_col = col
        elif header == "Adresse":
            address_col = col
    
    if not walkscore_col:
        print("❌ WalkScore column not found!")
        return
    
    print(f"✅ Found WalkScore column at position {walkscore_col}")
    
    # Analyze the data
    total_rows = ws.max_row - 1
    empty_walkscores = 0
    filled_walkscores = 0
    empty_addresses = 0
    
    print("\n🔍 Detailed Analysis:")
    
    for row in range(2, ws.max_row + 1):
        address = ws.cell(row=row, column=address_col).value if address_col else None
        walkscore = ws.cell(row=row, column=walkscore_col).value
        
        if not address or address == "None":
            empty_addresses += 1
        elif walkscore is None or walkscore == "":
            empty_walkscores += 1
        else:
            filled_walkscores += 1
    
    print(f"   Total listings: {total_rows}")
    print(f"   Listings with addresses: {total_rows - empty_addresses}")
    print(f"   Listings without addresses: {empty_addresses}")
    print(f"   WalkScores filled: {filled_walkscores}")
    print(f"   WalkScores empty (with addresses): {empty_walkscores}")
    
    # Show some examples of filled walkscores
    print(f"\n✅ Examples of listings WITH WalkScore:")
    count = 0
    for row in range(2, ws.max_row + 1):
        address = ws.cell(row=row, column=address_col).value if address_col else None
        walkscore = ws.cell(row=row, column=walkscore_col).value
        
        if walkscore and walkscore != "":
            print(f"   Row {row}: WalkScore {walkscore} | {address}")
            count += 1
            if count >= 5:  # Show first 5 examples
                break
    
    # Show some examples of empty walkscores
    print(f"\n❌ Examples of listings WITHOUT WalkScore:")
    count = 0
    for row in range(2, ws.max_row + 1):
        address = ws.cell(row=row, column=address_col).value if address_col else None
        walkscore = ws.cell(row=row, column=walkscore_col).value
        
        if address and address != "None" and (not walkscore or walkscore == ""):
            print(f"   Row {row}: EMPTY | {address}")
            count += 1
            if count >= 5:  # Show first 5 examples
                break
    
    print(f"\n💡 Solutions:")
    if empty_walkscores > 0:
        print(f"   1. Run 'python3 extended-parse.py' to fill {empty_walkscores} missing WalkScores")
        print(f"   2. The process may take time as it fetches data from walkscore.com")
        print(f"   3. Make sure your .env file has correct USER_DATA_DIR configured")
    
    if empty_addresses > 0:
        print(f"   4. {empty_addresses} listings have no addresses and cannot get WalkScores")
        print(f"   5. Check the data extraction process for address parsing issues")

if __name__ == "__main__":
    fix_walkscore_display()
