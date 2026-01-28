from pyairtable import Api
import os

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "properties")

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

records = table.all()
record_ids = [record['id'] for record in records]

if record_ids:
    table.batch_delete(record_ids)
    print(f"Deleted {len(record_ids)} records from properties table")
else:
    print("No records to delete")
