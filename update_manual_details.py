import sqlite3
import sys

if len(sys.argv) != 4:
    print("Usage: python update_manual_details.py <centris_id> <details_page_url> <note>")
    sys.exit(1)

centris_id = sys.argv[1]
details_page_url = sys.argv[2]
note = sys.argv[3]

conn = sqlite3.connect('centris.db')
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS manual_details (
    "Centris ID" TEXT PRIMARY KEY,
    "Details page" TEXT,
    "Note" TEXT
)
''')

if not details_page_url or details_page_url.strip() == "":
    cursor.execute('''
    INSERT OR REPLACE INTO manual_details ("Centris ID", "Details page", "Note")
    VALUES (?, (SELECT "Details page" FROM manual_details WHERE "Centris ID" = ?), ?)
    ''', (centris_id, centris_id, note))
else:
    cursor.execute('''
    INSERT OR REPLACE INTO manual_details ("Centris ID", "Details page", "Note")
    VALUES (?, ?, ?)
    ''', (centris_id, details_page_url, note))

conn.commit()
conn.close()

print(f"✅ Updated: {centris_id} -> {details_page_url} (Note: {note})")
