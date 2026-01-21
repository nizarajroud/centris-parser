import os
import time
import fire
import boto3
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
        # Use act_get instead of act to get the response
        result = nova.act_get(f"Go to walkscore.com, search for '{address}' and return the Walk Score number")
        
        if result and hasattr(result, 'response') and result.response:
            response = result.response.strip()
            print(f"WalkScore response: '{response}'")
            import re
            score_match = re.search(r'\b(\d{1,3})\b', response)
            if score_match:
                score = score_match.group(1)
                print(f"Extracted score: {score}")
                return score
        return ""
    except Exception as e:
        print(f"Error getting WalkScore: {e}")
        import traceback
        traceback.print_exc()
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
        result = nova.act_get("Look for 'Superficie du terrain' on this current page and return only its value (like '1 234 m²')")
        if result and hasattr(result, 'response') and result.response:
            response = result.response.strip()
            # Remove quotes if present
            if response.startswith('"') and response.endswith('"'):
                response = response[1:-1]
            print(f"Superficie response for {centris_url}: {response}")
            
            # Just return the raw response for now to see what we're getting
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
        result = nova.act_get(
            f"Go to maps.google.com. Search for '{dollard_address}' and press enter. "
            "Click Directions. "
            f"Enter '{property_address}' into the starting point field and press enter. "
            "Click the car icon for driving directions. "
            "Return the driving time in minutes only as a number."
        )
        if result and hasattr(result, 'response') and result.response:
            response = result.response.strip()
            print(f"Dollard response: '{response}'")
            import re
            # Extract number of minutes from response
            time_match = re.search(r'(\d+)', response)
            if time_match:
                time_minutes = time_match.group(1)
                print(f"Extracted time: {time_minutes} minutes")
                return time_minutes
        return ""
    except Exception as e:
        print(f"Error getting distance to Dollard: {e}")
        return ""


def main(user_data_dir: str = None, headless: bool = None, field: str = None) -> None:
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
    if field:
        # Direct field parameter provided
        field_options = ["WalkScore", "Dollard", "Superficie"]
        if field in field_options:
            selected_fields = [field]
        else:
            print(f"Invalid field '{field}'. Valid options: {', '.join(field_options)}")
            return
    else:
        # Show menu
        fzf = FzfPrompt()
        field_options = ["WalkScore", "Dollard", "Superficie"]
        selected_fields = fzf.prompt(field_options, "--prompt='Select fields to process (use TAB for multi-select): ' --multi")
        
        if not selected_fields:
            print("No fields selected. Exiting.")
            return

    extraction_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
    print(f"Using Excel file: {extraction_file}")
    
    # Load existing workbook
    try:
        wb = load_workbook(extraction_file)
        ws = wb.active
        print(f"Loaded workbook with {ws.max_row} rows and {ws.max_column} columns")
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
            print(f"Column {col}: {header}")
            if header == "Adresse":
                address_col = col
            elif header == "WalkScore":
                walkscore_col = col
            elif header == "Dollard":
                dollard_col = col
            elif header == "No Centris":
                centris_col = col
            elif header == "Superficie":
                superficie_col = col
        
        print(f"Found columns - Address: {address_col}, WalkScore: {walkscore_col}, Dollard: {dollard_col}")
        
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
                print(f"Row {row}: Current WalkScore value = '{current_walkscore}'")
                if not current_walkscore:
                    print(f"Getting WalkScore for row {row}: {address}")
                    walkscore = get_walkscore(address, nova)
                    if walkscore:
                        ws.cell(row=row, column=walkscore_col, value=int(walkscore))
                        wb.save(extraction_file)  # Save immediately after each update
                        print(f"Saved WalkScore {walkscore} for row {row}")
                    time.sleep(2)
                else:
                    print(f"Skipping row {row} - already has WalkScore: {current_walkscore}")
            
            # Process Dollard distance if selected and column exists and empty
            if "Dollard" in selected_fields and dollard_col and dollard_address and address:
                current_dollard = ws.cell(row=row, column=dollard_col).value
                print(f"Row {row}: Current Dollard value = '{current_dollard}'")
                if not current_dollard:
                    print(f"Getting distance to Dollard for row {row}: {address}")
                    dollard_time = HowFarFromDollard(dollard_address, address, nova)
                    if dollard_time:
                        ws.cell(row=row, column=dollard_col, value=int(dollard_time))
                        wb.save(extraction_file)  # Save immediately after each update
                        print(f"Saved Dollard {dollard_time} for row {row}")
                    time.sleep(2)
                else:
                    print(f"Skipping row {row} - already has Dollard: {current_dollard}")
            
            # Process Superficie du terrain if selected and column exists and empty
            if "Superficie" in selected_fields and superficie_col and centris_col:
                current_superficie = ws.cell(row=row, column=superficie_col).value
                print(f"Row {row}: Current SuperficieDuterrain value = '{current_superficie}'")
                if not current_superficie:
                    centris_cell = ws.cell(row=row, column=centris_col)
                    centris_url = centris_cell.hyperlink.target if centris_cell.hyperlink else ""
                    if centris_url:
                        print(f"Getting Superficie du terrain for row {row}: {centris_url}")
                        superficie = getSuperficieDuterrain(centris_url, nova)
                        if superficie:
                            ws.cell(row=row, column=superficie_col, value=superficie)
                            wb.save(extraction_file)  # Save immediately after each update
                            print(f"Saved SuperficieDuterrain {superficie} for row {row}")
                        time.sleep(2)
                    else:
                        print(f"No Centris URL found for row {row}")
                else:
                    print(f"Skipping row {row} - already has SuperficieDuterrain: {current_superficie}")
        
        # Final save at the end
        wb.save(extraction_file)
        print(f"Final save completed for {extraction_file}")
        print(f"Updated selected fields ({', '.join(selected_fields)}) in {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
