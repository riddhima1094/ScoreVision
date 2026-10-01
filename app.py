from flask import Flask, render_template, request
import pandas as pd
import joblib

app = Flask(__name__)


# ==============================
# Load Trained ML Model
# ==============================

model = joblib.load("model/scorevision_model.pkl")


# ==============================
# Feature Importance
# ==============================

feature_names = [
    "Age",
    "Attendance",
    "Study Hours",
    "Previous Score",
    "Assignment Marks",
    "Internal Marks",
    "Class Participation",
    "Sleep Hours",
    "Extracurricular Activity"
]

feature_importance = model.feature_importances_

important_features = sorted(
    zip(feature_names, feature_importance),
    key=lambda x: x[1],
    reverse=True
)

top_features = important_features[:3]


# ==============================
# Home Page
# ==============================

@app.route("/")
def home():

    return render_template("index.html")


# ==============================
# Prediction
# ==============================

@app.route("/predict", methods=["POST"])
def predict():

    # Get values from HTML form

    name = request.form["name"]

    age = float(request.form["age"])

    attendance = float(request.form["attendance"])

    study_hours = float(request.form["study_hours"])

    previous_score = float(request.form["previous_score"])

    assignment_marks = float(
        request.form["assignment_marks"]
    )

    internal_marks = float(
        request.form["internal_marks"]
    )

    participation = float(
        request.form["participation"]
    )

    sleep_hours = float(
        request.form["sleep_hours"]
    )

    extracurricular = int(
        request.form["extracurricular"]
    )


    # ==============================
    # Create Student Data
    # ==============================

    student_data = pd.DataFrame({

        "age": [age],

        "attendance": [attendance],

        "study_hours": [study_hours],

        "previous_score": [previous_score],

        "assignment_marks": [assignment_marks],

        "internal_marks": [internal_marks],

        "participation": [participation],

        "sleep_hours": [sleep_hours],

        "extracurricular": [extracurricular]

    })


    # ==============================
    # Make Prediction
    # ==============================

    predicted_score = model.predict(
        student_data
    )[0]


    # ==============================
    # Performance Category
    # ==============================

    if predicted_score >= 85:

        category = "Excellent"

    elif predicted_score >= 70:

        category = "Good"

    elif predicted_score >= 50:

        category = "Average"

    else:

        category = "Needs Improvement"


    # ==============================
    # Send Result to HTML
    # ==============================

    return render_template(

        "result.html",

        name=name,

        score=round(predicted_score, 2),

        category=category,

        top_features=top_features

    )


# ==============================
# Run Flask Application
# ==============================

if __name__ == "__main__":

    app.run(debug=True)