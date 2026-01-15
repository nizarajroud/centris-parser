# Copyright 2025 Amazon Inc

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""AWS Solutions to NotebookLM automation script.

Usage:
python nllm-aws-asl.py [user_data_dir] [--headless]
"""

import fire
import os
import time
from dotenv import load_dotenv
from pyfzf.pyfzf import FzfPrompt
from nova_act import NovaAct

load_dotenv()


def main(user_data_dir: str = None, headless: bool = None) -> None:
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



    with NovaAct(
        starting_page=os.getenv("STARTING_PAGE"),
        user_data_dir=user_data_dir,
        headless=headless,
        clone_user_data_dir=False,
    ) as nova:
        time.sleep(3)
        
        from bs4 import BeautifulSoup
        
        def extract_fields(soup):
            def extract_field(field_name):
                label = soup.find("span", class_="d-textStrong d-fontSize--smallest", string=lambda s: s and field_name in s)
                if not label:
                    label = soup.find("span", class_="d-textStrong", string=lambda s: s and field_name in s)
                if label:
                    parent = label.find_parent("div")
                    next_div = parent.find_next_sibling("div") if parent else None
                    if next_div:
                        value = next_div.find("span")
                        return value.get_text(strip=True) if value else ""
                return ""
            
            def extract_sdb_se():
                label = soup.find("span", class_="d-textStrong", string=lambda s: s and "SDB + SE" in s)
                if label:
                    parent = label.find_parent("div")
                    next_div = parent.find_next_sibling("div") if parent else None
                    if next_div:
                        formula = next_div.find("span", class_="formula J_formula")
                        return formula.get_text(strip=True) if formula else ""
                return ""
            
            def extract_details():
                details_elem = soup.find("span", class_="d-textSoft")
                return details_elem.get_text(strip=True) if details_elem else ""
            
            def extract_building_style():
                details = extract_details()
                if "Maison " in details and " dans le quartier" in details:
                    return details.split("Maison ")[1].split(" dans le quartier")[0]
                return ""
            
            def extract_neighborhood():
                details = extract_details()
                if " dans le quartier " in details and " construite en " in details:
                    return details.split(" dans le quartier ")[1].split(" construite en ")[0]
                return ""
            
            def extract_construction_year():
                details = extract_details()
                if " construite en " in details:
                    return details.split(" construite en ")[1]
                return ""
            
            def extract_badge():
                badge = soup.find("span", class_="badge mtx-subheader-badge")
                return badge.get_text(strip=True) if badge else ""
            
            def format_date(date_str):
                if not date_str:
                    return ""
                try:
                    from datetime import datetime
                    # Parse the date and calculate difference with current date
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                            date_obj = datetime(year, month, day)
                    elif '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) == 3:
                            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                            date_obj = datetime(year, month, day)
                    else:
                        return date_str
                    
                    current_date = datetime.now()
                    diff = (current_date - date_obj).days
                    
                    if diff == 0:
                        return "aujourd'hui"
                    elif diff == 1:
                        return "depuis 1 jour"
                    else:
                        return f"depuis {diff} jours"
                except:
                    return date_str
            
            def extract_street_address(address):
                if not address:
                    return ""
                if '(' in address and ')' in address:
                    # Pattern: <Adresse> <ville> <(secteur)>
                    return address.split(' (')[0].rsplit(' ', 1)[0]
                else:
                    # Pattern: <Adresse> <ville>
                    return address.rsplit(' ', 1)[0]
            
            def extract_city(address):
                if not address:
                    return ""
                if '(' in address and ')' in address:
                    # Pattern: <Adresse> <ville> <(secteur)>
                    return address.split(' (')[0].rsplit(' ', 1)[1]
                else:
                    # Pattern: <Adresse> <ville>
                    return address.rsplit(' ', 1)[1]
            
            def extract_sector(address):
                if not address:
                    return ""
                if '(' in address and ')' in address:
                    # Extract text between parentheses
                    return address.split('(')[1].split(')')[0]
                else:
                    # If no sector, use city value
                    return extract_city(address)
            
            centris_info = soup.find("span", class_="d-subtextSoft d-fontSize--smallest")
            centris_no = date_sent = ""
            if centris_info:
                parts = centris_info.get_text(separator="|").split("|")
                for part in parts:
                    if "No Centris" in part:
                        centris_no = part.split(":")[-1].strip()
                    elif "Date d'envoi" in part:
                        date_sent = part.split(":")[-1].strip()
            
            address_elem = soup.find("div", class_="col-sm-12 d-text d-fontSize--largest")
            address = ""
            if address_elem:
                link = address_elem.find("a")
                address = link.get_text(strip=True) if link else ""
            
            price_elem = soup.find("span", class_="d-text d-fontSize--larger")
            price = price_elem.get_text(strip=True) if price_elem else ""
            
            # Extract building type from description
            desc_elem = soup.find("span", class_="d-textSoft")
            building_type = ""
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                # Extract building type (first part before "in the")
                if " in the " in desc_text:
                    building_type = desc_text.split(" in the ")[0].strip()
            
            return {
                "Address": address,
                "Street Address": extract_street_address(address),
                "City": extract_city(address),
                "Sector": extract_sector(address),
                "Price": price,
                "Centris No.": centris_no,
                "Date d'app/maj": format_date(date_sent),
                "Building Type": extract_field("Type de bâtiment"),
                "Energy/Heating": extract_field("Énergie/Chauffage"),
                "Garage": extract_field("Garage"),
                "Rooms": extract_field("Pièces"),
                "Bedrooms": extract_field("Chambres"),
                "SDB + SE": extract_sdb_se(),
                "Fireplace-Stove": extract_field("Foyer-Poêle"),
                "Pool": extract_field("Piscine"),
                "Building Style": extract_building_style(),
                "Neighborhood": extract_neighborhood(),
                "Construction Year": extract_construction_year(),
                "Badge": extract_badge(),
            }
        
        soup = BeautifulSoup(nova.page.content(), "html.parser")
        listings = soup.find_all("div", class_="multiLineDisplay")
        
        from openpyxl import load_workbook, Workbook
        import sqlite3
        
        extraction_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
        
        # Load manual details from database
        manual_details_urls = {}
        try:
            conn = sqlite3.connect('centris.db')
            cursor = conn.cursor()
            cursor.execute('SELECT "Centris ID", "Details page" FROM manual_details')
            for row in cursor.fetchall():
                manual_details_urls[row[0]] = row[1]
            conn.close()
            print(f"Loaded {len(manual_details_urls)} URLs from database")
        except Exception as e:
            print(f"Warning: Could not load from database: {e}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(extraction_file), exist_ok=True)
        
        # Load existing workbook or create new one
        try:
            wb = load_workbook(extraction_file)
            ws = wb.active
        except:
            wb = Workbook()
            ws = wb.active
        
        # Add headers
        headers = ["No Centris", "details-page", "score_total", "Non_negociables_/65", "Souhaits_importants_/20", "Souhaits_secondaires_/15", "Adresse", "Prix", "Année de construction", "Ville", "Secteur", "WalkScore", "DollardDistance", "SuperficieDuterrain", "Style de bâtiment", 
                  "Garage", "Badge", "Date d'app/maj", "Quartier", "Adresse rue", "Type de bâtiment", "Pièces", 
                  "Énergie/Chauffage", "Chambres", "SDB + SE", "Foyer-Poêle", "Piscine"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Extract all listings first
        all_listings = []
        for i, listing in enumerate(listings, 1):
            print(f"Processing listing {i}/{len(listings)}...")
            fields = extract_fields(listing)
            
            # Set empty score columns and other fields (will be filled by other scripts if needed)
            centris_no = fields.get("Centris No.", "")
            # Get details page URL from database
            fields["details-page"] = manual_details_urls.get(centris_no, "")
            fields["score_total"] = ""
            
            fields["score_total"] = ""
            fields["Non_negociables_/65"] = ""
            fields["Souhaits_importants_/20"] = ""
            fields["Souhaits_secondaires_/15"] = ""
            fields["WalkScore"] = ""
            fields["DollardDistance"] = ""
            fields["SuperficieDuterrain"] = ""
            
            all_listings.append(fields)
        
        # Sort by construction year (most recent to oldest)
        def year_to_number(year_str):
            if not year_str:
                return -1
            try:
                return int(year_str)
            except:
                return -1
        
        all_listings.sort(key=lambda x: year_to_number(x.get("Construction Year", "")), reverse=True)
        
        # Load manual-details tab to get cells with embedded links
        manual_details_cells = {}
        try:
            if 'manual-details' in wb.sheetnames:
                manual_ws = wb['manual-details']
                for row_idx, row in enumerate(manual_ws.iter_rows(min_row=2), start=2):
                    if row[0].value:  # Centris No. in first column
                        centris_no = str(row[0].value).strip()
                        if len(row) > 1 and row[1]:  # Cell with link in second column
                            manual_details_cells[centris_no] = row[1]
                            print(f"Loaded manual-details: '{centris_no}' -> {row[1].value}")
                print(f"Loaded {len(manual_details_cells)} cells from manual-details tab")
            else:
                print("Warning: manual-details tab not found")
        except Exception as e:
            print(f"Warning: Could not load manual-details tab: {e}")
        
        # Write sorted listings starting from row 2
        for i, fields in enumerate(all_listings, 1):
            row = i + 1  # Row 2 is listing 1, row 3 is listing 2, etc.
            
            # Clean price to show only main price in XXX XXX $ format
            price = fields.get("Price", "")
            if price:
                import re
                matches = re.findall(r'\d{3}[\d\s,]*\s*\$', price)
                if matches:
                    # Take the first (main) price
                    main_price = matches[0].strip()
                    fields["Price"] = main_price
            
            # Map fields to columns
            field_map = {
                "Centris No.": 1,
                "details-page": 2,
                "score_total": 3,
                "Non_negociables_/65": 4,
                "Souhaits_importants_/20": 5,
                "Souhaits_secondaires_/15": 6,
                "Address": 7,
                "Price": 8,
                "Construction Year": 9,
                "City": 10,
                "Sector": 11,
                "WalkScore": 12,
                "DollardDistance": 13,
                "SuperficieDuterrain": 14,
                "Building Style": 15,
                "Garage": 16,
                "Badge": 17,
                "Date d'app/maj": 18,
                "Neighborhood": 19,
                "Street Address": 20,
                "Building Type": 21,
                "Rooms": 22,
                "Energy/Heating": 23,
                "Bedrooms": 24,
                "SDB + SE": 25,
                "Fireplace-Stove": 26,
                "Pool": 27
            }
            
            for field_name, col in field_map.items():
                value = fields.get(field_name, "")
                
                # Create hyperlink for Centris No.
                if field_name == "Centris No." and value:
                    centris_site = os.getenv('CENTRIS_SITE', '')
                    if centris_site:
                        ville = fields.get("City", "").lower().replace(" ", "-")
                        secteur = fields.get("Sector", "").lower().replace(" ", "-")
                        
                        # Remove parentheses and content within them from secteur
                        import re
                        secteur = re.sub(r'\([^)]*\)', '', secteur).strip().replace(" ", "-")
                        
                        if ville == secteur or not secteur:
                            url = f"{centris_site}maison~a-vendre~{ville}/{value}"
                        else:
                            url = f"{centris_site}maison~a-vendre~{ville}-{secteur}/{value}"
                        
                        # Create hyperlink
                        ws.cell(row=row, column=col).hyperlink = url
                        ws.cell(row=row, column=col).value = value
                        ws.cell(row=row, column=col).style = "Hyperlink"
                    else:
                        ws.cell(row=row, column=col, value=value)
                # Write details-page with hyperlink if URL exists
                elif field_name == "details-page" and value:
                    cell = ws.cell(row=row, column=col)
                    cell.hyperlink = value
                    cell.value = "More details"
                    cell.style = "Hyperlink"
                else:
                    ws.cell(row=row, column=col, value=value)
        
        wb.save(extraction_file)
        time.sleep(8)
        print(f"Extracted {len(listings)} listings to {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
