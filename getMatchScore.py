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


def scrape_centris_property(centris_url: str) -> Dict:
    """
    Extrait les informations d'une propriété depuis Centris.
    
    Args:
        centris_url: URL de la propriété sur Centris
        
    Returns:
        Dictionnaire contenant les informations de la propriété
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(centris_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire les informations clés (à adapter selon la structure Centris)
        property_data = {
            'url': centris_url,
            'html_content': response.text[:50000]  # Limiter pour éviter dépassement token
        }
        
        return property_data
        
    except Exception as e:
        raise Exception(f"Erreur lors du scraping Centris: {str(e)}")


def calculate_matching_score(
    google_sheet_url: str, 
    centris_url: str,
    aws_region: str = 'us-east-1'
) -> Tuple[float, Dict]:
    """
    Calcule le score de correspondance entre une propriété Centris et les critères
    définis dans un Google Sheet.
    
    Args:
        google_sheet_url: URL publique du Google Sheet contenant les critères
        centris_url: URL de la propriété sur Centris
        aws_region: Région AWS pour Bedrock (défaut: us-east-1)
        
    Returns:
        Tuple contenant:
            - score: Score total (0-100)
            - details: Dictionnaire avec détails de l'évaluation
    """
    
    # 1. Charger les critères depuis Google Sheet
    print("📊 Chargement des critères depuis Google Sheet...")
    criteria_df = get_google_sheet_as_dataframe(google_sheet_url)
    criteria_text = criteria_df.to_string()
    
    # 2. Scraper la propriété Centris
    print("🏠 Extraction des données de la propriété Centris...")
    property_data = scrape_centris_property(centris_url)
    
    # 3. Initialiser le client Bedrock avec boto3
    print("🤖 Initialisation du client AWS Bedrock...")
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=aws_region
    )
    
    # 4. Construire le prompt pour Claude
    prompt = f"""Tu es un expert en évaluation immobilière. Tu dois analyser une propriété et calculer un score de correspondance basé sur des critères de pondération précis.

# CRITÈRES DE PONDÉRATION
Voici le tableau des critères avec leurs poids respectifs:

{criteria_text}

# PROPRIÉTÉ À ÉVALUER
URL: {property_data['url']}

Voici le contenu HTML de la page Centris (extrait):
{property_data['html_content']}

# TÂCHE
1. Extraire toutes les caractéristiques pertinentes de la propriété depuis le HTML
2. Évaluer chaque critère du tableau de pondération
3. Attribuer les points selon les valeurs observées
4. Calculer le score total sur 100

# FORMAT DE RÉPONSE
Tu DOIS répondre UNIQUEMENT avec un JSON valide, sans aucun texte avant ou après. Format exact:

{{
  "score_total": <nombre entre 0 et 100>,
  "score_non_negociables": <score sur 65>,
  "score_souhaits_importants": <score sur 25>,
  "score_souhaits_secondaires": <score sur 10>,
  "evaluation_detaillee": [
    {{
      "critere": "<nom du critère>",
      "poids_max": <poids maximum>,
      "points_obtenus": <points obtenus>,
      "justification": "<explication courte>",
      "valeur_observee": "<valeur trouvée dans l'annonce>"
    }}
  ],
  "points_forts": ["<point fort 1>", "<point fort 2>", ...],
  "points_faibles": ["<point faible 1>", "<point faible 2>", ...],
  "informations_manquantes": ["<info manquante 1>", "<info manquante 2>", ...],
  "recommandation": "<EXCELLENT|TRÈS BON|ACCEPTABLE|LIMITE|À REJETER>",
  "conseil": "<conseil personnalisé basé sur l'analyse>"
}}

Réponds UNIQUEMENT avec le JSON, rien d'autre."""

    # 5. Appeler Claude via Bedrock
    print("⚡ Analyse en cours avec Claude Opus 4.5...")
    
    try:
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-opus-4-5-20251101-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            })
        )
        
        # Parse la réponse de Bedrock
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text']
        
    except Exception as e:
        raise Exception(f"Erreur lors de l'appel à Bedrock: {str(e)}")
    
    # 6. Parser la réponse JSON de Claude
    try:
        # Nettoyer la réponse pour extraire uniquement le JSON
        response_text = response_text.strip()
        
        # Enlever les backticks markdown si présents
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            # Enlever le dernier ```
            if response_text.endswith('```'):
                response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        score = result['score_total']
        details = result
        
        print(f"\n✅ Score calculé: {score}/100")
        print(f"   📋 Non-négociables: {result['score_non_negociables']}/65")
        print(f"   📋 Souhaits importants: {result['score_souhaits_importants']}/25")
        print(f"   📋 Souhaits secondaires: {result['score_souhaits_secondaires']}/10")
        print(f"   🎯 Recommandation: {result['recommandation']}")
        
        return score, details
        
    except json.JSONDecodeError as e:
        raise Exception(f"Erreur lors du parsing JSON: {str(e)}\nRéponse reçue: {response_text[:500]}")


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


# Exemple d'utilisation
if __name__ == "__main__":
    # URLs d'exemple
    GOOGLE_SHEET_URL = os.getenv('PONDERATION_SHEET_URL')
    CENTRIS_URL = os.getenv('CENTRIS_URL')
    
    if not GOOGLE_SHEET_URL or not CENTRIS_URL:
        print("❌ Erreur: Les variables d'environnement PONDERATION_SHEET_URL et CENTRIS_URL doivent être définies dans le fichier .env")
        exit(1)
    
    try:
        score, details = calculate_matching_score(
            google_sheet_url=GOOGLE_SHEET_URL,
            centris_url=CENTRIS_URL,
            aws_region='us-east-1'
        )
        
        # Afficher le rapport complet
        display_evaluation_report(details)
        
        # Optionnel: Sauvegarder le résultat en JSON
        output_file = 'evaluation_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(details, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Résultats sauvegardés dans: {output_file}")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")