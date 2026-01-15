import sqlite3

# Create database and table
conn = sqlite3.connect('centris.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS manual_details (
    "Centris ID" TEXT PRIMARY KEY,
    "Details page" TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database created: centris.db")
print("✅ Table created: manual_details")
