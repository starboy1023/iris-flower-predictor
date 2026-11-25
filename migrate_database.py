
import os
import sqlite3
import turso_serverless
from dotenv import load_dotenv

# Load Turso credentials
load_dotenv()

database_url = os.getenv("TURSO_DATABASE_URL")
auth_token = os.getenv("TURSO_AUTH_TOKEN")

# Connect to your existing local SQLite database
local_connection = sqlite3.connect("iris_predictions.db")
local_connection.row_factory = sqlite3.Row

# Retrieve existing predictions
local_predictions = local_connection.execute("""
    SELECT * FROM predictions
    ORDER BY id
""").fetchall()

print("Local predictions found:", len(local_predictions))

# Connect to Turso
cloud_connection = turso_serverless.connect(
    database_url,
    auth_token=auth_token
)

cloud_connection.row_factory = turso_serverless.Row

# Create predictions table in Turso
cloud_connection.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sepal_length REAL NOT NULL,
        sepal_width REAL NOT NULL,
        petal_length REAL NOT NULL,
        petal_width REAL NOT NULL,
        predicted_species TEXT NOT NULL,
        confidence REAL NOT NULL,
        prediction_date TEXT NOT NULL
    )
""")

# Transfer records to Turso
for item in local_predictions:

    cloud_connection.execute("""
        INSERT OR IGNORE INTO predictions (
            id,
            sepal_length,
            sepal_width,
            petal_length,
            petal_width,
            predicted_species,
            confidence,
            prediction_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item["id"],
        item["sepal_length"],
        item["sepal_width"],
        item["petal_length"],
        item["petal_width"],
        item["predicted_species"],
        item["confidence"],
        item["prediction_date"]
    ))

cloud_connection.commit()

# Verify migrated records
cloud_count = cloud_connection.execute("""
    SELECT COUNT(*) FROM predictions
""").fetchone()[0]

print("Migration completed!")
print("Predictions now in Turso:", cloud_count)

local_connection.close()
cloud_connection.close()
