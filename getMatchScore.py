import requests
import pandas as pd
from bs4 import BeautifulSoup
import boto3
import json
from typing import Dict, Tuple
import re
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Setup logging
LOG_TO_FILE = os.getenv('LOG_MATCHSCORE_ON_FILE', '0') == '1'
log_file = None
if LOG_TO_FILE:
    os.makedirs('logs', exist_ok=True)
    timestamp = datetime.now().strftime("%d-%M-%S")
    log_file = open(f'logs/getMatchScore-{timestamp}.log', 'w', encoding='utf-8')

def log_print(message):
    """Print to console or log file based on LOG_MATCHSCORE_ON_FILE setting"""
    if LOG_TO_FILE:
        if log_file:
            log_file.write(message + '\n')
            log_file.flush()
    else:
        print(message)


def getSouhaitSecondaireScore(centris_num: str, aws_region: str = 'ca-central-1') -> float:
    """
    Get Souhaits Secondaires score from Amazon Bedrock agent.
    
    Args:
        centris_num: Centris number
        aws_region: AWS region for Bedrock agent
        
    Returns:
        float: Score finale value
    """
    try:
        bedrock_agent = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name=aws_region
        )
        
        agent_id = os.getenv('BEDROCK_AGENT_ID', 'HomeAgent')
        agent_alias_id = os.getenv('BEDROCK_AGENT_ALIAS_ID', 'HomeAgent')
        knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'RMS7YSFH2W')
        prompt = f"Score total pour categorie SOUHAITS SECONDAIRES pour centris num {centris_num}"
        
        log_print(f"Calling Bedrock agent {agent_id} (alias: {agent_alias_id}) for centris {centris_num}")
        log_print(f"Prompt: {prompt}")
        
        response = bedrock_agent.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=f'session-{centris_num}',
            inputText=prompt,
            sessionState={
                'knowledgeBaseConfigurations': [{
                    'knowledgeBaseId': knowledge_base_id,
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'filter': {
                                'stringContains': {
                                    'key': 'x-amz-bedrock-kb-source-uri',
                                    'value': centris_num
                                }
                            }
                        }
                    }
                }]
            }
        )
        
        # Extract response text and references
        response_text = ""
        all_references = []
        
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    response_text += chunk['bytes'].decode('utf-8')
                # Check for citations in chunk
                if 'attribution' in chunk and 'citations' in chunk['attribution']:
                    for citation in chunk['attribution']['citations']:
                        if 'retrievedReferences' in citation:
                            for ref in citation['retrievedReferences']:
                                if 'location' in ref:
                                    if 's3Location' in ref['location']:
                                        uri = ref['location']['s3Location'].get('uri', 'Unknown URI')
                                        all_references.append(uri)
                                    elif 'webLocation' in ref['location']:
                                        uri = ref['location']['webLocation'].get('url', 'Unknown URL')
                                        all_references.append(uri)
            elif 'trace' in event:
                trace = event['trace']
                if 'orchestrationTrace' in trace:
                    orch_trace = trace['orchestrationTrace']
                    if 'observation' in orch_trace:
                        observation = orch_trace['observation']
                        if 'knowledgeBaseLookupOutput' in observation:
                            kb_output = observation['knowledgeBaseLookupOutput']
                            if 'retrievedReferences' in kb_output:
                                for ref in kb_output['retrievedReferences']:
                                    if 'location' in ref:
                                        if 's3Location' in ref['location']:
                                            uri = ref['location']['s3Location'].get('uri', 'Unknown URI')
                                            all_references.append(uri)
                                        elif 'webLocation' in ref['location']:
                                            uri = ref['location']['webLocation'].get('url', 'Unknown URL')
                                            all_references.append(uri)
        
        log_print(f"Agent response: {response_text}")
        
        if all_references:
            log_print(f"Reference URLs used ({len(all_references)} total):")
            for i, ref in enumerate(all_references, 1):
                log_print(f"  [{i}] {ref}")
        else:
            log_print("No reference URLs found in response")
        
        # Extract score finale value from different possible formats
        import re
        
        # Try multiple regex patterns to match different response formats
        patterns = [
            r'SCORE TOTAL - SOUHAITS SECONDAIRES:\s*(\d+\.?\d*)\s*/\s*\d+',  # Original format
            r'score total.*SOUHAITS SECONDAIRES.*?(\d+\.?\d*)\s*/\s*\d+',    # Flexible format
            r'(\d+\.?\d*)\s*/\s*15\s*points?',                               # X / 15 points format
            r'(\d+\.?\d*)\s*/\s*\d+\s*points?'                               # X / Y points format
        ]
        
        score = 0.0
        for pattern in patterns:
            score_match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if score_match:
                score = float(score_match.group(1))
                log_print(f"Extracted score using pattern '{pattern}': {score}")
                return score
        
        log_print("No score found with any pattern")
        log_print(f"Full response text: {response_text}")
        return 0.0
            
    except Exception as e:
        error_msg = str(e)
        log_print(f"Error calling Bedrock agent for {centris_num}: {error_msg}")
        log_print(f"Agent ID: {agent_id}")
        log_print(f"Agent Alias ID: {agent_alias_id}")
        log_print(f"Knowledge Base ID: {knowledge_base_id}")
        log_print(f"AWS Region: {aws_region}")
        print(f"Error calling Bedrock agent for {centris_num}: {error_msg}")
        return 0.0


def get_google_sheet_as_dataframe(sheet_url: str) -> pd.DataFrame:
    """
    Convertit un Google Sheet public en DataFrame pandas.
    
    Args:
        sheet_url: URL publique du Google Sheet
        
    Returns:
        DataFrame contenant les données du sheet
    """
    # Extraire l'ID du sheet et convertir en format export CSV
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, sheet_url)
    
    if not match:
        raise ValueError("URL Google Sheet invalide")
    
    sheet_id = match.group(1)
    export_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
    
    try:
        df = pd.read_csv(export_url)
        return df
    except Exception as e:
        raise Exception(f"Erreur lors du chargement du Google Sheet: {str(e)}")


def scrape_centris_property(centris_url: str, centris_number: str, extraction_file_path: str, ponderation_sheet_path: str) -> Dict:
    """
    Extrait les informations d'une propriété depuis Excel ou HTML selon la colonne Origine.
    
    Args:
        centris_url: URL de la propriété
        centris_number: Numéro Centris
        extraction_file_path: Chemin vers le fichier Excel d'extraction
        ponderation_sheet_path: Chemin vers le fichier de pondération
        
    Returns:
        Dictionnaire contenant les informations de la propriété
    """
    import pandas as pd
    from openpyxl import load_workbook
    
    # Load ponderation criteria
    criteria_df = get_google_sheet_as_dataframe(ponderation_sheet_path)
    
    # Load extraction file
    wb = load_workbook(extraction_file_path)
    ws = wb.active
    
    # Find columns
    col_indices = {}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header == "No Centris":
            col_indices['centris'] = col
        elif header == "Origine":
            col_indices['origine'] = col
    
    # Find property row
    property_row_data = {}
    origine = "HTML"  # default
    
    for row in range(2, ws.max_row + 1):
        if str(ws.cell(row=row, column=col_indices['centris']).value) == str(centris_number):
            # Get all row data
            for col in range(1, ws.max_column + 1):
                header = ws.cell(row=1, column=col).value
                value = ws.cell(row=row, column=col).value
                if header:
                    property_row_data[header] = value
            
            # Get origine if column exists
            if 'origine' in col_indices:
                origine = ws.cell(row=row, column=col_indices['origine']).value or "HTML"
            break
    
    property_data = {
        'url': centris_url,
        'centris_number': centris_number,
        'origine': origine,
        'excel_data': property_row_data,
        'criteria': criteria_df.to_string()
    }
    
    if origine == "HTML":
        # Scrape HTML content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(centris_url, headers=headers)
            response.raise_for_status()
            property_data['html_content'] = response.text[:50000]
        except Exception as e:
            property_data['html_content'] = f"Error scraping: {str(e)}"
    
    return property_data


def calculate_matching_score(
    ponderation_sheet_path: str, 
    centris_url: str,
    centris_number: str,
    extraction_file_path: str,
    aws_region: str = 'us-east-1'
) -> Tuple[float, float, float, float]:
    """
    Calcule le score de correspondance entre une propriété et les critères.
    """
    import pandas as pd
    from openpyxl import load_workbook
    
    # 1. Load criteria and property data
    criteria_df = get_google_sheet_as_dataframe(ponderation_sheet_path)
    property_data = scrape_centris_property(centris_url, centris_number, extraction_file_path, ponderation_sheet_path)
    
    # 2. Initialize Bedrock client
    bedrock = boto3.client(service_name='bedrock-runtime', region_name=aws_region)
    
    # 3. Initialize scores
    total_score = 0
    score_non_negociables = 0
    score_souhaits_importants = 0
    score_souhaits_secondaires = 0
    
    # Lists to track calculations
    non_neg_details = []
    important_details = []
    secondaire_details = []
    
    log_print(f"\ncentris no {centris_number}:")
    log_print(f"Total criteria rows to process: {len(criteria_df)}")
    
    # Group criteria by name to handle multiple ranges
    processed_criteria = set()
    current_category = None
    criteria_count_by_category = {'Non-négociables': 0, 'Souhaits importants': 0, 'Souhaits secondaires': 0}
    
    for idx, criteria_row in criteria_df.iterrows():
        # Map the actual column positions
        rang = criteria_row.iloc[0] if len(criteria_row) > 0 else ''
        origine = criteria_row.iloc[1] if len(criteria_row) > 1 else ''
        critere = criteria_row.iloc[2] if len(criteria_row) > 2 else ''
        poids = criteria_row.iloc[3] if len(criteria_row) > 3 else 0
        valeur = criteria_row.iloc[4] if len(criteria_row) > 4 else ''
        poids_effectif = criteria_row.iloc[5] if len(criteria_row) > 5 else 0
        
        # Skip invalid criteria (nan source, decision recommendations, etc.)
        if pd.isna(origine) or not critere or critere in ['Critère', 'Validation', 'Décision recommandée'] or any(emoji in critere for emoji in ['🟢', '🟡', '🟠', '🔴', '⛔', '✓']):
            continue
            
        if critere in processed_criteria:
            continue
            
        # Determine category based on row position
        if idx <= 45:  # Non-négociables section
            categorie = 'Non-négociables'
        elif idx <= 80:  # Souhaits importants section  
            categorie = 'Souhaits importants'
        else:  # Souhaits secondaires section
            categorie = 'Souhaits secondaires'
        
        # Skip HTML criteria completely
        if origine and str(origine).lower() == 'html':
            continue
        
        # Check if we're transitioning to a new category
        if current_category and current_category != categorie:
            # Log the previous category total
            if current_category == 'Non-négociables':
                log_print(f"  Non-négociables category total: {' + '.join(non_neg_details)} = {score_non_negociables}")
            elif current_category == 'Souhaits importants':
                log_print(f"  Souhaits importants category total: {' + '.join(important_details)} = {score_souhaits_importants}")
            elif current_category == 'Souhaits secondaires':
                log_print(f"  Souhaits secondaires category total: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
        
        current_category = categorie
        
        log_print(f"  Processing: {critere} (Source: {origine}, Category: {categorie})")
        criteria_count_by_category[categorie] += 1
        
        # Get all ranges for this criteria
        all_ranges = []
        current_critere = critere
        
        # Start from current row and look for all related rows
        for idx2 in range(idx, len(criteria_df)):
            row2 = criteria_df.iloc[idx2]
            critere2 = row2.iloc[2] if len(row2) > 2 else ''
            valeur2 = row2.iloc[4] if len(row2) > 4 else ''
            poids_effectif2 = row2.iloc[5] if len(row2) > 5 else 0
            
            # If we find the same criteria name or an empty criteria name with a value and weight
            if (critere2 == current_critere) or (pd.isna(critere2) and valeur2 and not pd.isna(poids_effectif2) and poids_effectif2 != 0):
                if valeur2 and not pd.isna(poids_effectif2) and poids_effectif2 != 0:
                    all_ranges.append((str(valeur2).strip(), float(poids_effectif2)))
            # Stop when we hit a new criteria (non-empty critere2 that's different)
            elif critere2 and not pd.isna(critere2) and critere2 != current_critere:
                break
        
        log_print(f"    Found {len(all_ranges)} ranges: {all_ranges}")
        
        awarded_points = 0.0
        
        # Get property value based on origine
        if origine and str(origine).lower() == 'excel':
            # Get from Excel columns
            property_value = property_data['excel_data'].get(critere)
            if property_value is None:
                # Try variations
                for key in property_data['excel_data'].keys():
                    if critere.lower().replace(' ', '').replace('-', '') in key.lower().replace(' ', '').replace('-', ''):
                        property_value = property_data['excel_data'][key]
                        break
            
            # Check property value against all ranges
            if property_value:
                prop_val_str = str(property_value).strip().replace(' ', '').replace('$', '').replace(',', '')
                
                for valeur_range, poids_range in all_ranges:
                    valeur_str = str(valeur_range).strip()
                    
                    log_print(f"      Comparing '{property_value}' vs '{valeur_range}'")
                    
                    # Check for numeric range
                    if '-' in valeur_str and any(char.isdigit() for char in valeur_str):
                        try:
                            range_parts = valeur_str.replace('$', '').replace('pc', '').replace(' ', '').split('-')
                            if len(range_parts) == 2:
                                min_val = float(range_parts[0])
                                max_val = float(range_parts[1])
                                prop_num = float(''.join(filter(str.isdigit, prop_val_str)))
                                
                                if min_val <= prop_num <= max_val:
                                    awarded_points = float(poids_range)
                                    log_print(f"    {critere} (Excel): {property_value} in range {valeur_range} -> {awarded_points} pts")
                                    break
                        except:
                            pass
                    
                    # Check for exact match
                    elif str(property_value).strip().lower() == valeur_str.lower():
                        awarded_points = float(poids_range)
                        log_print(f"    {critere} (Excel): {property_value} matches {valeur_range} -> {awarded_points} pts")
                        break
                
                if awarded_points == 0:
                    log_print(f"    {critere} (Excel): {property_value} -> No match found -> 0 pts")
        
        # Add to appropriate category
        if categorie == 'Non-négociables':
            score_non_negociables += awarded_points
            non_neg_details.append(str(awarded_points))
        elif categorie == 'Souhaits importants':
            score_souhaits_importants += awarded_points
            important_details.append(str(awarded_points))
        elif categorie == 'Souhaits secondaires':
            score_souhaits_secondaires += awarded_points
            secondaire_details.append(str(awarded_points))
        
        total_score += awarded_points
        processed_criteria.add(critere)
    
    # Log the final category total
    if current_category == 'Non-négociables':
        log_print(f"  Non-négociables category total: {' + '.join(non_neg_details)} = {score_non_negociables}")
    elif current_category == 'Souhaits importants':
        log_print(f"  Souhaits importants category total: {' + '.join(important_details)} = {score_souhaits_importants}")
    elif current_category == 'Souhaits secondaires':
        log_print(f"  Souhaits secondaires category total: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
    
    # Add special log for Souhaits secondaires processing via Bedrock agent
    log_print(f"  Processing Souhaits secondaires via Bedrock agent...")
    
    # Print calculation summary
    log_print(f"  Criteria processed by category: {criteria_count_by_category}")
    log_print(f"  Non-négociables: {' + '.join(non_neg_details)} = {score_non_negociables}")
    log_print(f"  Souhaits importants: {' + '.join(important_details)} = {score_souhaits_importants}")
    log_print(f"  Souhaits secondaires: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
    log_print(f"  TOTAL: {total_score}")
    
    return total_score, score_non_negociables, score_souhaits_importants, score_souhaits_secondaires


def display_evaluation_report(details: Dict) -> None:
    """
    Affiche un rapport formaté de l'évaluation.
    
    Args:
        details: Dictionnaire contenant les détails de l'évaluation
    """
    print("\n" + "="*80)
    print("📊 RAPPORT D'ÉVALUATION DÉTAILLÉ")
    print("="*80)
    
    print(f"\n🎯 SCORE GLOBAL: {details['score_total']}/100 - {details['recommandation']}")
    
    print("\n📈 RÉPARTITION DES SCORES:")
    print(f"  • Non-négociables: {details['score_non_negociables']}/65 pts")
    print(f"  • Souhaits importants: {details['score_souhaits_importants']}/20 pts")
    print(f"  • Souhaits secondaires: {details['score_souhaits_secondaires']}/15 pts")
    
    print("\n✅ POINTS FORTS:")
    for i, point in enumerate(details['points_forts'], 1):
        print(f"  {i}. {point}")
    
    print("\n❌ POINTS FAIBLES:")
    for i, point in enumerate(details['points_faibles'], 1):
        print(f"  {i}. {point}")
    
    if details['informations_manquantes']:
        print("\n⚠️  INFORMATIONS MANQUANTES À VÉRIFIER:")
        for i, info in enumerate(details['informations_manquantes'], 1):
            print(f"  {i}. {info}")
    
    print(f"\n💡 CONSEIL:")
    print(f"  {details['conseil']}")
    
    print("\n" + "="*80)
    print("📋 ÉVALUATION DÉTAILLÉE PAR CRITÈRE")
    print("="*80)
    
    for item in details['evaluation_detaillee']:
        emoji = "✅" if item['points_obtenus'] == item['poids_max'] else \
                "⚠️" if item['points_obtenus'] > 0 else "❌"
        print(f"\n{emoji} {item['critere']}")
        print(f"   Score: {item['points_obtenus']}/{item['poids_max']} pts")
        print(f"   Valeur: {item['valeur_observee']}")
        print(f"   Justification: {item['justification']}")


def process_all_properties_from_excel(
    ponderation_sheet_path: str,
    extraction_file_path: str,
    aws_region: str = 'us-east-1'
) -> None:
    """
    Process all properties from Excel file using details-page embedded URLs.
    
    Args:
        ponderation_sheet_path: Path to ponderation criteria sheet
        extraction_file_path: Path to extraction Excel file
        aws_region: AWS region for Bedrock
    """
    from openpyxl import load_workbook
    
    # Load workbook
    wb = load_workbook(extraction_file_path)
    ws = wb.active
    
    # Find column indices
    col_indices = {}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header == "No Centris":
            col_indices['centris'] = col
        elif header == "details-page":
            col_indices['details'] = col
        elif header == "score_total":
            col_indices['total'] = col
        elif header == "Non_negociables_/65":
            col_indices['non_neg'] = col
        elif header == "Souhaits_importants_/20":
            col_indices['important'] = col
        elif header == "Souhaits_secondaires_/15":
            col_indices['secondaire'] = col
    
    # Process each row
    for row in range(2, ws.max_row + 1):
        centris_no = ws.cell(row=row, column=col_indices['centris']).value
        details_cell = ws.cell(row=row, column=col_indices['details'])
        
        if not centris_no or not details_cell.hyperlink:
            continue
            
        property_url = details_cell.hyperlink.target
        print(f"Processing {centris_no}: {property_url}")
        
        if LOG_TO_FILE:
            print("in progress")
        
        try:
            total, non_neg, important, secondaire = calculate_matching_score(
                ponderation_sheet_path=ponderation_sheet_path,
                centris_url=property_url,
                centris_number=str(centris_no),
                extraction_file_path=extraction_file_path,
                aws_region=aws_region
            )
            
            # Get Souhaits Secondaires score from Bedrock agent
            log_print(f"Getting Souhaits Secondaires score for {centris_no}...")
            secondaire_from_agent = getSouhaitSecondaireScore(str(centris_no), 'ca-central-1')
            log_print(f"Received score from agent: {secondaire_from_agent}")
            
            # Calculate total score including all categories
            total_with_agent = total + secondaire_from_agent
            
            # Update scores in Excel
            ws.cell(row=row, column=col_indices['total'], value=total_with_agent)
            ws.cell(row=row, column=col_indices['non_neg'], value=non_neg)
            ws.cell(row=row, column=col_indices['important'], value=important)
            ws.cell(row=row, column=col_indices['secondaire'], value=secondaire_from_agent)
            
            log_print(f"Updated Excel - Secondaire column with value: {secondaire_from_agent}")
            
            # Force save after each update
            wb.save(extraction_file_path)
            log_print(f"Saved Excel file")
            
            print(f"✅ {centris_no}: Total={total_with_agent} (Non-neg={non_neg} + Important={important} + Secondaire={secondaire_from_agent})")
            print(f"   Saved to Excel: row {row}, columns {col_indices}")
            
        except Exception as e:
            print(f"❌ Error processing {centris_no}: {str(e)}")
    
    # Save workbook
    wb.save(extraction_file_path)
    print(f"✅ All scores updated in {extraction_file_path}")
    
    # Close log file if open
    if LOG_TO_FILE and log_file:
        log_file.close()


# Exemple d'utilisation
if __name__ == "__main__":
    PONDERATION_SHEET_PATH = os.getenv('PONDERATION_SHEET_PATH')
    EXTRACTION_CENTRIS = os.getenv('EXTRACTION_CENTRIS')
    
    if not PONDERATION_SHEET_PATH or not EXTRACTION_CENTRIS:
        print("❌ Erreur: Les variables d'environnement PONDERATION_SHEET_PATH et EXTRACTION_CENTRIS doivent être définies dans le fichier .env")
        exit(1)
    
    try:
        process_all_properties_from_excel(
            ponderation_sheet_path=PONDERATION_SHEET_PATH,
            extraction_file_path=EXTRACTION_CENTRIS,
            aws_region='us-east-1'
        )
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")