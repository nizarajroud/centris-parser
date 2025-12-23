import requests
import pandas as pd
from bs4 import BeautifulSoup
import boto3
import json
from typing import Dict, Tuple
import re
import os
from dotenv import load_dotenv

load_dotenv()


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
    
    print(f"\ncentris no {centris_number}:")
    print(f"Total criteria rows to process: {len(criteria_df)}")
    
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
        
        # Skip header rows and empty rows
        if not critere or critere in ['Critère', 'Validation'] or pd.isna(critere):
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
        
        # Check if we're transitioning to a new category
        if current_category and current_category != categorie:
            # Log the previous category total
            if current_category == 'Non-négociables':
                print(f"  Non-négociables category total: {' + '.join(non_neg_details)} = {score_non_negociables}")
            elif current_category == 'Souhaits importants':
                print(f"  Souhaits importants category total: {' + '.join(important_details)} = {score_souhaits_importants}")
            elif current_category == 'Souhaits secondaires':
                print(f"  Souhaits secondaires category total: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
        
        current_category = categorie
        
        print(f"  Processing: {critere} (Source: {origine}, Category: {categorie})")
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
        
        print(f"    Found {len(all_ranges)} ranges: {all_ranges}")
        
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
                    
                    print(f"      Comparing '{property_value}' vs '{valeur_range}'")
                    
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
                                    print(f"    {critere} (Excel): {property_value} in range {valeur_range} -> {awarded_points} pts")
                                    break
                        except:
                            pass
                    
                    # Check for exact match
                    elif str(property_value).strip().lower() == valeur_str.lower():
                        awarded_points = float(poids_range)
                        print(f"    {critere} (Excel): {property_value} matches {valeur_range} -> {awarded_points} pts")
                        break
                
                if awarded_points == 0:
                    print(f"    {critere} (Excel): {property_value} -> No match found -> 0 pts")
            
        else:
            # HTML processing - use Claude for the first range only (simplified)
            if all_ranges:
                valeur_first = all_ranges[0][0]
                poids_first = all_ranges[0][1]
                
                prompt = f"""Analyse cette page web pour le critère: {critere}

CRITÈRE: {critere}
VALEUR ATTENDUE: {valeur_first}
POINTS: {poids_first}

CONTENU HTML:
{property_data.get('html_content', 'No HTML')[:1500]}

Réponds uniquement en JSON:
{{"correspond": true/false, "valeur_trouvee": "<valeur>", "points": <{poids_first} si correspond, 0 sinon>}}"""

                try:
                    response = bedrock.invoke_model(
                        modelId="us.anthropic.claude-opus-4-5-20251101-v1:0",
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 300,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1
                        })
                    )
                    
                    response_body = json.loads(response['body'].read())
                    response_text = response_body['content'][0]['text'].strip()
                    
                    if '```' in response_text:
                        response_text = response_text.split('```')[1]
                        if response_text.startswith('json'):
                            response_text = response_text[4:]
                        response_text = response_text.split('```')[0]
                    
                    result = json.loads(response_text.strip())
                    awarded_points = float(result.get('points', 0))
                    valeur_trouvee = result.get('valeur_trouvee', 'N/A')
                    
                    print(f"    {critere} (HTML): {valeur_trouvee} -> {awarded_points} pts")
                    
                except Exception as e:
                    awarded_points = 0.0
                    print(f"    {critere} (HTML): Error -> 0 pts")
        
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
        print(f"  Non-négociables category total: {' + '.join(non_neg_details)} = {score_non_negociables}")
    elif current_category == 'Souhaits importants':
        print(f"  Souhaits importants category total: {' + '.join(important_details)} = {score_souhaits_importants}")
    elif current_category == 'Souhaits secondaires':
        print(f"  Souhaits secondaires category total: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
    
    # Print calculation summary
    print(f"  Criteria processed by category: {criteria_count_by_category}")
    print(f"  Non-négociables: {' + '.join(non_neg_details)} = {score_non_negociables}")
    print(f"  Souhaits importants: {' + '.join(important_details)} = {score_souhaits_importants}")
    print(f"  Souhaits secondaires: {' + '.join(secondaire_details)} = {score_souhaits_secondaires}")
    print(f"  TOTAL: {total_score}")
    
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
    print(f"  • Souhaits importants: {details['score_souhaits_importants']}/25 pts")
    print(f"  • Souhaits secondaires: {details['score_souhaits_secondaires']}/10 pts")
    
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
        elif header == "score_non_negociables":
            col_indices['non_neg'] = col
        elif header == "score_souhaits_importants":
            col_indices['important'] = col
        elif header == "score_souhaits_secondaires":
            col_indices['secondaire'] = col
    
    # Process each row
    for row in range(2, ws.max_row + 1):
        centris_no = ws.cell(row=row, column=col_indices['centris']).value
        details_cell = ws.cell(row=row, column=col_indices['details'])
        
        if not centris_no or not details_cell.hyperlink:
            continue
            
        property_url = details_cell.hyperlink.target
        print(f"Processing {centris_no}: {property_url}")
        
        try:
            total, non_neg, important, secondaire = calculate_matching_score(
                ponderation_sheet_path=ponderation_sheet_path,
                centris_url=property_url,
                centris_number=str(centris_no),
                extraction_file_path=extraction_file_path,
                aws_region=aws_region
            )
            
            # Update scores in Excel
            ws.cell(row=row, column=col_indices['total'], value=total)
            ws.cell(row=row, column=col_indices['non_neg'], value=non_neg)
            ws.cell(row=row, column=col_indices['important'], value=important)
            ws.cell(row=row, column=col_indices['secondaire'], value=secondaire)
            
            # Force save after each update
            wb.save(extraction_file_path)
            
            print(f"✅ {centris_no}: Total={total}, Non-neg={non_neg}, Important={important}, Secondaire={secondaire}")
            print(f"   Saved to Excel: row {row}, columns {col_indices}")
            
        except Exception as e:
            print(f"❌ Error processing {centris_no}: {str(e)}")
    
    # Save workbook
    wb.save(extraction_file_path)
    print(f"✅ All scores updated in {extraction_file_path}")


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