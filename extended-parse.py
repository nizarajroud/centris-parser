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


def HowFarFromDollard(dollard_address: str, property_address: str, nova) -> str:
    """Calculate driving time in minutes from property to Dollard address using Google Maps"""
    if not dollard_address or not property_address:
        return ""
    
    try:
        result = nova.act(
            f"Go to maps.google.com. Search for '{dollard_address}' and press enter. "
            "Click Directions. "
            f"Enter '{property_address}' into the starting point field and press enter. "
            "Click the car icon for driving directions. "
            "Return the driving time in minutes only as a number."
        )
        if result and hasattr(result, 'response') and result.response:
            import re
            # Extract number of minutes from response
            time_match = re.search(r'(\d+)', result.response)
            if time_match:
                return time_match.group(1)
        return ""
    except Exception as e:
        print(f"Error getting distance to Dollard: {e}")
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
        
        # Find address, walkscore, and dollard distance columns
        address_col = None
        walkscore_col = None
        dollard_col = None
        
        for col in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col).value
            if header == "Adresse":
                address_col = col
            elif header == "WalkScore":
                walkscore_col = col
            elif header == "DollardDistance":
                dollard_col = col
        
        if not address_col:
            print("Could not find Adresse column")
            return
        
        dollard_address = os.getenv('DOLLARD_ADRESS', '')
        
        # Process each row
        for row in range(2, ws.max_row + 1):
            address = ws.cell(row=row, column=address_col).value
            
            if address:
                # Process WalkScore if column exists and empty
                if walkscore_col:
                    current_walkscore = ws.cell(row=row, column=walkscore_col).value
                    if not current_walkscore:
                        print(f"Getting WalkScore for row {row}: {address}")
                        walkscore = get_walkscore(address, nova)
                        ws.cell(row=row, column=walkscore_col, value=walkscore)
                        time.sleep(2)
                
                # Process Dollard distance if column exists and empty
                if dollard_col and dollard_address:
                    current_dollard = ws.cell(row=row, column=dollard_col).value
                    if not current_dollard:
                        print(f"Getting distance to Dollard for row {row}: {address}")
                        dollard_time = HowFarFromDollard(dollard_address, address, nova)
                        ws.cell(row=row, column=dollard_col, value=dollard_time)
                        time.sleep(2)
        
        wb.save(extraction_file)
        print(f"Updated WalkScores and Dollard distances in {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
