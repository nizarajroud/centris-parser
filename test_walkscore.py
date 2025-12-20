import os
from dotenv import load_dotenv
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

user_data_dir = os.getenv('USER_DATA_DIR')

with NovaAct(
    starting_page="https://www.walkscore.com/",
    user_data_dir=user_data_dir,
    headless=True,
    clone_user_data_dir=False,
) as nova:
    score = get_walkscore("5140 Rue Hubert-Guertin Longueuil (Saint-Hubert)", nova)
    print(f"Final score: {score}")
