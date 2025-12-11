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
        
        # nova.act("Click on the second home listing")
        time.sleep(2)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(nova.page.content(), "html.parser")
        
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
        
        # Extract Centris No., Date Sent
        centris_info = soup.find("span", class_="d-subtextSoft d-fontSize--smallest")
        centris_no = date_sent = ""
        if centris_info:
            parts = centris_info.get_text(separator="|").split("|")
            for part in parts:
                if "Centris No." in part:
                    centris_no = part.split(":")[-1].strip()
                elif "Date Sent" in part:
                    date_sent = part.split(":")[-1].strip()
 
        
        fields = {
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
        
        with open("first_home_details.txt", "w", encoding="utf-8") as f:
            for key, value in fields.items():
                f.write(f"{key}: {value}\n")


if __name__ == "__main__":
    fire.Fire(main)
