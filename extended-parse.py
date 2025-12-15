import os
import time
import fire
from dotenv import load_dotenv
from pyfzf.pyfzf import FzfPrompt
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


def getSuperficieDuterrain(centris_url: str, nova) -> str:
    """Get Superficie du terrain from Centris property page"""
    if not centris_url:
        return ""
    
    try:
        # Navigate directly using page.goto to ensure we're on the right page
        nova.page.goto(centris_url)
        time.sleep(5)  # Wait longer for page to fully load
        
        # Get the current URL to verify we're on the right page
        current_url = nova.page.url
        print(f"Navigated to: {current_url}")
        
        # Extract the Superficie du terrain value from this specific page
        result = nova.act("Look for 'Superficie du terrain' on this current page and return only its value (like '1 234 m²')")
        if result and hasattr(result, 'response') and result.response:
            response = result.response.strip()
            print(f"Superficie response for {centris_url}: {response}")
            
            # Extract measurement values and convert to m²
            import re
            match = re.search(r'([\d\s,]+)\s*(m²|sq\s*ft|pi²|pieds?)', response, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(' ', '').replace(',', '')
                unit = match.group(2).lower()
                
                try:
                    value = float(value_str)
                    
                    # Convert to m²
                    if 'sq' in unit or 'pi' in unit or 'pied' in unit or 'pc' in unit:
                        # Convert square feet to m² (1 sq ft = 0.092903 m²)
                        value_m2 = value * 0.092903
                    else:
                        # Already in m²
                        value_m2 = value
                    
                    return f"{value_m2:.0f} m²"
                except ValueError:
                    return response
            
            # If no pattern found but response exists, return it
            if response and len(response) < 50:
                return response
                
        return ""
    except Exception as e:
        print(f"Error getting Superficie du terrain from {centris_url}: {e}")
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
    
    if user_data_dir is None:
        user_data_dir = os.getenv('USER_DATA_DIR')
        if user_data_dir is None:
            raise ValueError("USER_DATA_DIR must be provided either as parameter or in .env file")
    
    if headless is None:
        headless_env = os.getenv('HEADLESS')
        if headless_env == '1':
            headless = True
        else:
            fzf = FzfPrompt()
            options = ["Visible (you can see the browser)", "Headless (background, faster)"]
            choice = fzf.prompt(options, "--prompt='Select browser mode: '")
            headless = choice and "Headless" in choice[0]

    # Select which fields to process
    fzf = FzfPrompt()
    field_options = ["WalkScore", "DollardDistance", "SuperficieDuterrain"]
    selected_fields = fzf.prompt(field_options, "--prompt='Select fields to process (use TAB for multi-select): ' --multi")
    
    if not selected_fields:
        print("No fields selected. Exiting.")
        return

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
        
        # Find address, walkscore, dollard distance, and superficie columns
        address_col = None
        walkscore_col = None
        dollard_col = None
        centris_col = None
        superficie_col = None
        
        for col in range(1, ws.max_column + 1):
            header = ws.cell(row=1, column=col).value
            if header == "Adresse":
                address_col = col
            elif header == "WalkScore":
                walkscore_col = col
            elif header == "DollardDistance":
                dollard_col = col
            elif header == "No Centris":
                centris_col = col
            elif header == "SuperficieDuterrain":
                superficie_col = col
        
        if not address_col:
            print("Could not find Adresse column")
            return
        
        dollard_address = os.getenv('DOLLARD_ADRESS', '')
        
        # Process each row
        for row in range(2, ws.max_row + 1):
            address = ws.cell(row=row, column=address_col).value if address_col else ""
            
            # Process WalkScore if selected and column exists and empty
            if "WalkScore" in selected_fields and walkscore_col and address:
                current_walkscore = ws.cell(row=row, column=walkscore_col).value
                if not current_walkscore:
                    print(f"Getting WalkScore for row {row}: {address}")
                    walkscore = get_walkscore(address, nova)
                    ws.cell(row=row, column=walkscore_col, value=walkscore)
                    time.sleep(2)
            
            # Process Dollard distance if selected and column exists and empty
            if "DollardDistance" in selected_fields and dollard_col and dollard_address and address:
                current_dollard = ws.cell(row=row, column=dollard_col).value
                if not current_dollard:
                    print(f"Getting distance to Dollard for row {row}: {address}")
                    dollard_time = HowFarFromDollard(dollard_address, address, nova)
                    ws.cell(row=row, column=dollard_col, value=dollard_time)
                    time.sleep(2)
            
            # Process Superficie du terrain if selected and column exists and empty
            if "SuperficieDuterrain" in selected_fields and superficie_col and centris_col:
                current_superficie = ws.cell(row=row, column=superficie_col).value
                if not current_superficie:
                    centris_cell = ws.cell(row=row, column=centris_col)
                    centris_url = centris_cell.hyperlink.target if centris_cell.hyperlink else ""
                    if centris_url:
                        print(f"Getting Superficie du terrain for row {row}: {centris_url}")
                        superficie = getSuperficieDuterrain(centris_url, nova)
                        ws.cell(row=row, column=superficie_col, value=superficie)
                        time.sleep(2)
        
        wb.save(extraction_file)
        print(f"Updated selected fields ({', '.join(selected_fields)}) in {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
