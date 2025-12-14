import os
import time
import fire
from dotenv import load_dotenv
from openpyxl import load_workbook
from nova_act import NovaAct

load_dotenv()


def get_walkscore(address: str, nova) -> str:
    """Get WalkScore for given address"""
    if not address:
        return ""
    
    try:
        result = nova.act(f"Go to walkscore.com, search for '{address}' and return the Walk Score number")
        if result and hasattr(result, 'response') and result.response:
            import re
            score_match = re.search(r'\b(\d{1,3})\b', result.response)
            if score_match:
                return score_match.group(1)
        return ""
    except Exception as e:
        print(f"Error getting WalkScore: {e}")
        return ""


def main(user_data_dir: str = None, headless: bool = None) -> None:
    """Process WalkScore for existing listings in Excel file"""
    
    if headless is None:
        choice = input("Run in headless mode? (y/n): ").strip().lower()
        headless = choice in ['y', 'yes']

    extraction_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
    
    # Load existing workbook
    try:
        wb = load_workbook(extraction_file)
        ws = wb.active
    except Exception as e:
        print(f"Error loading file {extraction_file}: {e}")
        return

    with NovaAct(
        starting_page="https://www.walkscore.com/",
        user_data_dir=user_data_dir,
        headless=headless,
        clone_user_data_dir=False,
    ) as nova:
        
        # Find address and walkscore columns
        address_col = None
        walkscore_col = None
        
        for col in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col).value
            if header == "Adresse":
                address_col = col
            elif header == "WalkScore":
                walkscore_col = col
        
        if not address_col or not walkscore_col:
            print("Could not find Adresse or WalkScore columns")
            return
        
        # Process each row
        for row in range(2, ws.max_row + 1):
            address = ws.cell(row=row, column=address_col).value
            current_walkscore = ws.cell(row=row, column=walkscore_col).value
            
            # Skip if already has WalkScore
            if current_walkscore:
                continue
                
            if address:
                print(f"Getting WalkScore for row {row}: {address}")
                walkscore = get_walkscore(address, nova)
                ws.cell(row=row, column=walkscore_col, value=walkscore)
                time.sleep(2)  # Rate limiting
        
        wb.save(extraction_file)
        print(f"Updated WalkScores in {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
