
import os
import turso_serverless
from dotenv import load_dotenv

load_dotenv()

connection = turso_serverless.connect(
    os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN")
)

# Configure database rows
connection.row_factory = turso_serverless.Row

# Create a temporary test table
connection.execute("""
    CREATE TABLE IF NOT EXISTS driver_test (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT
    )
""")

connection.execute(
    "INSERT INTO driver_test (message) VALUES (?)",
    ("Turso is working!",)
)

connection.commit()

# Retrieve a record
result = connection.execute("""
    SELECT id, message
    FROM driver_test
    ORDER BY id DESC
    LIMIT 1
""").fetchone()

print("Database test successful!")
print("Message:", result["message"])
print("Record ID:", result["id"])

connection.close()
