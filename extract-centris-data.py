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
        starting_page="https://matrix.centris.ca/Matrix/Public/Portal.aspx?ID=0-3516933858-10&eml=bml6YXIuYWpyb3VkQGdtYWlsLmNvbQ==&L=1#1",
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
            
            centris_info = soup.find("span", class_="d-subtextSoft d-fontSize--smallest")
            centris_no = date_sent = ""
            if centris_info:
                parts = centris_info.get_text(separator="|").split("|")
                for part in parts:
                    if "Centris No." in part:
                        centris_no = part.split(":")[-1].strip()
                    elif "Date Sent" in part:
                        date_sent = part.split(":")[-1].strip()
            
            address_elem = soup.find("div", class_="col-sm-12 d-text d-fontSize--largest")
            address = ""
            if address_elem:
                link = address_elem.find("a")
                address = link.get_text(strip=True) if link else ""
            
            price_elem = soup.find("span", class_="d-text d-fontSize--larger")
            price = price_elem.get_text(strip=True) if price_elem else ""
            
            return {
                "Address": address,
                "Price": price,
                "Centris No.": centris_no,
                "Date Sent": date_sent,
                "Building Type": extract_field("Building Type"),
                "Energy/Heating": extract_field("Energy/Heating"),
                "Garage": extract_field("Garage"),
                "Rooms": extract_field("Rooms"),
                "Bedrooms": extract_field("Bedrooms"),
                "Bath + PR": extract_field("Bath + PR"),
                "Fireplace-Stove": extract_field("Fireplace-Stove"),
                "Pool": extract_field("Pool"),
            }
        
        soup = BeautifulSoup(nova.page.content(), "html.parser")
        listings = soup.find_all("div", class_="multiLineDisplay")
        
        from openpyxl import load_workbook
        
        extraction_file = os.getenv('EXTRACTION_CENTRIS', 'extraction-centris.xlsx')
        
        # Load existing workbook
        wb = load_workbook(extraction_file)
        ws = wb.active
        
        # Extract and fill listings starting from column B
        for i, listing in enumerate(listings, 1):
            print(f"Processing listing {i}/{len(listings)}...")
            fields = extract_fields(listing)
            col = i + 1  # Column B is 2, C is 3, etc.
            
            # Map fields to rows
            field_map = {
                "Address": 5,
                "Price": 4,
                "Centris No.": 2,
                "Date Sent": 3,
                "Building Type": 6,
                "Energy/Heating": 7,
                "Garage": 8,
                "Rooms": 9,
                "Bedrooms": 10,
                "Bath + PR": 11,
                "Fireplace-Stove": 12,
                "Pool": 13
            }
            
            for field_name, row in field_map.items():
                ws.cell(row=row, column=col, value=fields.get(field_name, ""))
        
        wb.save(extraction_file)
        print(f"Extracted {len(listings)} listings to {extraction_file}")


if __name__ == "__main__":
    fire.Fire(main)
