import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Create database and table
db_path = os.getenv('CENTRIS_DB_PATH', 'centris.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS manual_details (
    "Centris ID" TEXT PRIMARY KEY,
    "Details page" TEXT,
    "Note" TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database created: centris.db")
print("✅ Table created: manual_details")
