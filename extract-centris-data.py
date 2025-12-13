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
        # starting_page="https://matrix.centris.ca/Matrix/Public/Portal.aspx?ID=0-3516933858-10&eml=bml6YXIuYWpyb3VkQGdtYWlsLmNvbQ==&L=1#1",
        starting_page="https://matrix.centris.ca/Matrix/Public/Portal.aspx?ID=0-3521571244-10&eml=bml6YXIuYWpyb3VkQGdtYWlsLmNvbQ==&L=2",
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
            
            def format_date(date_str):
                if not date_str:
                    return ""
                try:
                    from datetime import datetime
                    months = {
                        'janvier': 'janvier', 'février': 'février', 'mars': 'mars', 'avril': 'avril',
                        'mai': 'mai', 'juin': 'juin', 'juillet': 'juillet', 'août': 'août',
                        'septembre': 'septembre', 'octobre': 'octobre', 'novembre': 'novembre', 'décembre': 'décembre'
                    }
                    # Parse various date formats and convert to "DD mois YYYY"
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            day, month, year = parts
                            month_name = list(months.values())[int(month) - 1]
                            return f"{int(day)} {month_name} {year}"
                    elif '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) == 3:
                            year, month, day = parts
                            month_name = list(months.values())[int(month) - 1]
                            return f"{int(day)} {month_name} {year}"
                    return date_str
                except:
                    return date_str
            
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
                "Price": price,
                "Centris No.": centris_no,
                "Date Sent": format_date(date_sent),
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
            }
        
        soup = BeautifulSoup(nova.page.content(), "html.parser")
        listings = soup.find_all("div", class_="multiLineDisplay")
        
        from openpyxl import load_workbook, Workbook
        
        extraction_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
        
        # Load existing workbook or create new one
        try:
            wb = load_workbook(extraction_file)
        except:
            wb = Workbook()
        ws = wb.active
        
        # Clear entire worksheet
        ws.delete_rows(1, ws.max_row)
        
        # Add headers
        headers = ["No Centris", "Adresse", "Prix", "Date d'envoi", "Type de bâtiment", 
                  "Énergie/Chauffage", "Garage", "Pièces", "Chambres", "SDB + SE", 
                  "Foyer-Poêle", "Piscine", "Style de bâtiment", "Quartier", "Année de construction"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Extract all listings first
        all_listings = []
        for i, listing in enumerate(listings, 1):
            print(f"Processing listing {i}/{len(listings)}...")
            fields = extract_fields(listing)
            all_listings.append(fields)
        
        # Sort by price (high to low)
        def price_to_number(price_str):
            if not price_str:
                return -1
            try:
                # Extract prices starting with $ and having at least 3 digits
                import re
                matches = re.findall(r'\$\d{3}[\d,]*', price_str)
                if matches:
                    prices = [int(match.replace('$', '').replace(',', '')) for match in matches]
                    return max(prices)
                return -1
            except:
                return -1
        
        all_listings.sort(key=lambda x: price_to_number(x.get("Price", "")), reverse=True)
        
        # Write sorted listings starting from row 2
        for i, fields in enumerate(all_listings, 1):
            row = i + 1  # Row 2 is listing 1, row 3 is listing 2, etc.
            
            # Clean price to show only main price in XXX XXX $ format
            price = fields.get("Price", "")
            if price:
                import re
                matches = re.findall(r'\$\d{3}[\d,]*', price)
                if matches:
                    prices = [int(match.replace('$', '').replace(',', '')) for match in matches]
                    main_price = max(prices)
                    fields["Price"] = f"{main_price:,}".replace(',', ' ') + " $"
            
            # Map fields to columns
            field_map = {
                "Centris No.": 1,
                "Address": 2,
                "Price": 3,
                "Date Sent": 4,
                "Building Type": 5,
                "Energy/Heating": 6,
                "Garage": 7,
                "Rooms": 8,
                "Bedrooms": 9,
                "SDB + SE": 10,
                "Fireplace-Stove": 11,
                "Pool": 12,
                "Building Style": 13,
                "Neighborhood": 14,
                "Construction Year": 15
            }
            
            for field_name, col in field_map.items():
                ws.cell(row=row, column=col, value=fields.get(field_name, ""))
        
        wb.save(extraction_file)
        time.sleep(8)
        print(f"Extracted {len(listings)} listings to {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
