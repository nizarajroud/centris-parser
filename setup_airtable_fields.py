from pyairtable import Api
import os

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

fields = [
    ("Date", "singleLineText"),
    ("Badge", "singleLineText"),
    ("No Centris", "singleLineText"),
    ("details-page", "url"),
    ("score_total", "number"),
    ("Non_negociables_/65", "number"),
    ("Souhaits_importants_/20", "number"),
    ("Souhaits_secondaires_/15", "number"),
    ("Adresse", "singleLineText"),
    ("Prix", "singleLineText"),
    ("Year", "number"),
    ("Ville", "singleLineText"),
    ("Secteur", "singleLineText"),
    ("WalkScore", "number"),
    ("Dollard", "number"),
    ("Superficie", "number"),
    ("Style", "singleLineText"),
    ("Garage", "singleLineText"),
    ("Quartier", "singleLineText"),
    ("Adresse rue", "singleLineText"),
    ("Type", "singleLineText"),
    ("Pièces", "singleLineText"),
    ("Énergie/Chauffage", "singleLineText"),
    ("Chambres", "singleLineText"),
    ("SDB + SE", "singleLineText"),
    ("Foyer-Poêle", "singleLineText"),
    ("Piscine", "singleLineText")
]

api = Api(AIRTABLE_API_KEY)
base = api.base(AIRTABLE_BASE_ID)

# Create new table
try:
    field_schemas = []
    for name, field_type in fields:
        field_schema = {"name": name, "type": field_type}
        if field_type == "number":
            field_schema["options"] = {"precision": 0}
        field_schemas.append(field_schema)
    
    table_schema = base.create_table("properties", field_schemas)
    print(f"Created table 'properties' with {len(fields)} fields")
except Exception as e:
    print(f"Error creating table: {e}")
