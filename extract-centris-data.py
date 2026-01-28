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
                "Date": format_date(date_sent),
                "Type": extract_field("Type de bâtiment"),
                "Energy/Heating": extract_field("Énergie/Chauffage"),
                "Garage": extract_field("Garage"),
                "Rooms": extract_field("Pièces"),
                "Bedrooms": extract_field("Chambres"),
                "SDB + SE": extract_sdb_se(),
                "Fireplace-Stove": extract_field("Foyer-Poêle"),
                "Pool": extract_field("Piscine"),
                "Style": extract_building_style(),
                "Neighborhood": extract_neighborhood(),
                "Year": extract_construction_year(),
                "Badge": extract_badge(),
            }
        
        soup = BeautifulSoup(nova.page.content(), "html.parser")
        listings = soup.find_all("div", class_="multiLineDisplay")
        
        from pyairtable import Api
        import sqlite3
        
        # Airtable configuration
        AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
        AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
        AIRTABLE_TABLE_NAME = "properties"
        
        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        
        # Load manual details from database
        manual_details_urls = {}
        try:
            db_path = os.getenv('CENTRIS_DB_PATH', 'centris.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT "Centris ID", "Details page" FROM manual_details')
            for row in cursor.fetchall():
                manual_details_urls[row[0]] = row[1]
            conn.close()
            print(f"Loaded {len(manual_details_urls)} URLs from database")
        except Exception as e:
            print(f"Warning: Could not load from database: {e}")
        
        # Extract all listings first
        all_listings = []
        for i, listing in enumerate(listings, 1):
            print(f"Processing listing {i}/{len(listings)}...")
            fields = extract_fields(listing)
            
            # Set empty score columns and other fields (will be filled by other scripts if needed)
            centris_no = fields.get("Centris No.", "")
            
            # Check database and insert if needed
            if centris_no:
                try:
                    db_path = os.getenv('CENTRIS_DB_PATH', 'centris.db')
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT "Details page" FROM manual_details WHERE "Centris ID" = ?', (centris_no,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        fields["details-page"] = existing[0]
                        print(f"Found existing record for {centris_no}, using URL: {existing[0]}")
                    else:
                        # Build Centris URL
                        centris_site = os.getenv('CENTRIS_SITE', '')
                        if centris_site:
                            ville = fields.get("City", "").lower().replace(" ", "-")
                            secteur = fields.get("Sector", "").lower().replace(" ", "-")
                            import re
                            secteur = re.sub(r'\([^)]*\)', '', secteur).strip().replace(" ", "-")
                            
                            if ville == secteur or not secteur:
                                centris_url = f"{centris_site}maison~a-vendre~{ville}/{centris_no}"
                            else:
                                centris_url = f"{centris_site}maison~a-vendre~{ville}-{secteur}/{centris_no}"
                            
                            cursor.execute('''
                                INSERT INTO manual_details ("Centris ID", "Details page", "Note")
                                VALUES (?, ?, ?)
                            ''', (centris_no, centris_url, "Auto-added from Centris URL"))
                            conn.commit()
                            fields["details-page"] = centris_url
                            print(f"Inserted new record for {centris_no} with URL: {centris_url}")
                        else:
                            fields["details-page"] = ""
                    conn.close()
                except Exception as e:
                    print(f"Warning: Could not check/update database for {centris_no}: {e}")
                    fields["details-page"] = manual_details_urls.get(centris_no, "")
            else:
                fields["details-page"] = ""
            
            # Clean price to show only main price in XXX XXX $ format
            price = fields.get("Price", "")
            if price:
                import re
                matches = re.findall(r'\d{3}[\d\s,]*\s*\$', price)
                if matches:
                    fields["Price"] = matches[0].strip()
            
            all_listings.append(fields)
        
        # Sort by date (most recent first)
        def date_to_days(date_str):
            if not date_str:
                return -1
            if "aujourd'hui" in date_str:
                return 0
            if "depuis" in date_str and "jour" in date_str:
                import re
                match = re.search(r'(\d+)', date_str)
                if match:
                    return int(match.group(1))
            return -1
        
        def year_to_number(year_str):
            if not year_str:
                return -1
            try:
                return int(year_str)
            except:
                return -1
        
        all_listings.sort(key=lambda x: date_to_days(x.get("Date", "")))
        
        # Insert or update records in Airtable
        existing_records = {r['fields'].get('No Centris'): r['id'] for r in table.all() if 'No Centris' in r['fields']}
        
        for fields in all_listings:
            centris_no = fields.get("Centris No.", "")
            record = {
                "Date": fields.get("Date", ""),
                "Badge": fields.get("Badge", ""),
                "No Centris": centris_no,
                "details-page": fields.get("details-page", ""),
                "Adresse": fields.get("Address", ""),
                "Prix": fields.get("Price", ""),
                "Year": year_to_number(fields.get("Year", "")),
                "Ville": fields.get("City", ""),
                "Secteur": fields.get("Sector", ""),
                "Style": fields.get("Style", ""),
                "Garage": fields.get("Garage", ""),
                "Quartier": fields.get("Neighborhood", ""),
                "Adresse rue": fields.get("Street Address", ""),
                "Type": fields.get("Type", ""),
                "Pièces": fields.get("Rooms", ""),
                "Énergie/Chauffage": fields.get("Energy/Heating", ""),
                "Chambres": fields.get("Bedrooms", ""),
                "SDB + SE": fields.get("SDB + SE", ""),
                "Foyer-Poêle": fields.get("Fireplace-Stove", ""),
                "Piscine": fields.get("Pool", "")
            }
            
            if centris_no in existing_records:
                table.update(existing_records[centris_no], record)
            else:
                table.create(record)
        
        time.sleep(8)
        print(f"Extracted {len(listings)} listings to Airtable")


if __name__ == "__main__":
    fire.Fire(main)
