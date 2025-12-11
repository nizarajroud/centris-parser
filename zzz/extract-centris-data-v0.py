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
        
        result = nova.act("Click on the first home listing and extract all details")
        
        parts = result.response.split(", ")
        fields = {
            "Address": parts[0] if len(parts) > 0 else "",
            "Type": parts[1] if len(parts) > 1 else "",
            "Price": parts[2] if len(parts) > 2 else "",
            "Style": parts[3] if len(parts) > 3 else "",
            "Lot Size": parts[4] if len(parts) > 4 else "",
            "Living Area": parts[5] if len(parts) > 5 else "",
            "Rooms": parts[6] if len(parts) > 6 else "",
            "Bathrooms": parts[7] if len(parts) > 7 else "",
            "Parking": parts[8] if len(parts) > 8 else "",
        }
        
        with open("first_home_details.txt", "w", encoding="utf-8") as f:
            for key, value in fields.items():
                f.write(f"{key}: {value}\n")
        
        print("First home details saved to first_home_details.txt")
        input("Press Enter to close the browser...")


if __name__ == "__main__":
    fire.Fire(main)
