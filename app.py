
from flask import Flask, render_template, request
import joblib
import numpy as np
import os
import turso_serverless
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

app = Flask(__name__)

# Load the trained model
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "iris_model.pkl")

model = joblib.load(MODEL_PATH)

def get_db_connection():
    connection = turso_serverless.connect(
        os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN")
    )

    connection.row_factory = turso_serverless.Row

    return connection


# Create database table
def create_database():

    connection = get_db_connection()

    connection.execute("""
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

    connection.commit()
    connection.close()


# Initialise database
create_database()

# Flower species
species = ["Setosa", "Versicolor", "Virginica"]


# Homepage
@app.route("/")
def home():
    return render_template("index.html")

# Prediction history route
@app.route("/history")
def history():

    connection = get_db_connection()

    predictions = connection.execute("""
        SELECT * FROM predictions
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "history.html",
        predictions=predictions
    )


# Analytics dashboard route
@app.route("/dashboard")
def dashboard():

    connection = get_db_connection()

    # Get total number of predictions
    total_predictions = connection.execute("""
        SELECT COUNT(*) FROM predictions
    """).fetchone()[0]

    # Count predictions for each flower species
    species_counts = connection.execute("""
        SELECT predicted_species, COUNT(*) AS total
        FROM predictions
        GROUP BY predicted_species
    """).fetchall()

    # Get recent prediction records
    recent_predictions = connection.execute("""
        SELECT * FROM predictions
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    connection.close()

    # Prepare chart data
    chart_labels = ["Setosa", "Versicolor", "Virginica"]

    chart_values = []

    for flower in chart_labels:
        count = 0

        for item in species_counts:
            if item["predicted_species"] == flower:
                count = item["total"]

        chart_values.append(count)

    return render_template(
        "dashboard.html",
        total_predictions=total_predictions,
        chart_labels=chart_labels,
        chart_values=chart_values,
        recent_predictions=recent_predictions
    )


# Prediction route
@app.route("/predict", methods=["POST"])
def predict():

    # Collect measurements
    measurements = {
        "sepal_length": float(request.form["sepal_length"]),
        "sepal_width": float(request.form["sepal_width"]),
        "petal_length": float(request.form["petal_length"]),
        "petal_width": float(request.form["petal_width"])
    }

    # Prepare input for the model
    input_data = np.array([[
        measurements["sepal_length"],
        measurements["sepal_width"],
        measurements["petal_length"],
        measurements["petal_width"]
    ]])

    # Predict species
    prediction = model.predict(input_data)[0]

    # Get probability estimates
    probabilities = model.predict_proba(input_data)[0]

    # Get predicted species name
    predicted_species = species[prediction]

    # Get confidence percentage
    confidence = round(float(max(probabilities)) * 100, 2)

    # Save prediction to database
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO predictions (
            sepal_length,
            sepal_width,
            petal_length,
            petal_width,
            predicted_species,
            confidence,
            prediction_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        measurements["sepal_length"],
        measurements["sepal_width"],
        measurements["petal_length"],
        measurements["petal_width"],
        predicted_species,
        confidence,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    connection.commit()
    connection.close()

    # Prepare probabilities for all species
    probability_results = [
        {
            "name": species[i],
            "percentage": round(float(probabilities[i]) * 100, 2)
        }
        for i in range(len(species))
    ]

    return render_template(
        "index.html",
        prediction=predicted_species,
        confidence=confidence,
        probability_results=probability_results,
        measurements=measurements
    )


if __name__ == "__main__":
    app.run(debug=True)
