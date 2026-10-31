from flask import Flask, render_template, request
import pandas as pd
import joblib

# Member 2 imports
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import text

from config import Config
from database.db import db

# Models - database tables register karne ke liye
from models.user import User
from models.academic_record import AcademicRecord
from models.prediction import Prediction
from models.cms import Lecture, Test, Question, TestSubmission

# API routes
from routes.auth import auth_bp
from routes.prediction import prediction_bp
from routes.dashboard import dashboard_bp
from routes.cms import cms_bp


# ============================================================
# CREATE FLASK APP
# ============================================================

app = Flask(__name__)

# Member 2 configuration
app.config.from_object(Config)

# Enable frontend/API communication
CORS(app)

# Initialize database
db.init_app(app)

# Initialize JWT
jwt = JWTManager(app)


# ============================================================
# JWT ERROR HANDLERS
# ============================================================

@jwt.unauthorized_loader
def missing_token_callback(error_string):
    return {
        "status": "error",
        "error": "Missing authorization token",
        "message": "Authorization header is required."
    }, 401


@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return {
        "status": "error",
        "error": "Invalid token",
        "message": "The provided authorization token is invalid."
    }, 401


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {
        "status": "error",
        "error": "Token expired",
        "message": "Please log in again."
    }, 401


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

with app.app_context():
    db.create_all()


# ============================================================
# REGISTER MEMBER 2 API BLUEPRINTS
# ============================================================

app.register_blueprint(
    auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    prediction_bp,
    url_prefix="/api/prediction"
)

app.register_blueprint(
    dashboard_bp,
    url_prefix="/api/dashboard"
)

app.register_blueprint(
    cms_bp,
    url_prefix="/api/cms"
)


# ============================================================
# LOAD MEMBER 1 MACHINE LEARNING MODEL
# ============================================================

model = joblib.load(
    "model/scorevision_model.pkl"
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

feature_names = [
    "Age",
    "Attendance",
    "Study Hours",
    "Previous Score",
    "Assignment Marks",
    "Internal Marks",
    "Class Participation",
    "Extracurricular Activity"
]

feature_importance = model.feature_importances_

important_features = sorted(
    zip(feature_names, feature_importance),
    key=lambda x: x[1],
    reverse=True
)

top_features = important_features[:3]


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "member3.html"
    )

@app.route("/dashboard")
def dashboard():
    return render_template("member3.html")

@app.route("/calculator")
@app.route("/ml-predict")
def ml_calculator():
    return render_template("index.html")
# ============================================================
# MEMBER 1 ML PREDICTION
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    try:

        # Get values from HTML form

        name = request.form["name"]

        age = float(
            request.form["age"]
        )

        attendance = float(
            request.form["attendance"]
        )

        study_hours = float(
            request.form["study_hours"]
        )

        previous_score = float(
            request.form["previous_score"]
        )

        assignment_marks = float(
            request.form["assignment_marks"]
        )

        internal_marks = float(
            request.form["internal_marks"]
        )

        participation = float(
            request.form["participation"]
        )


        extracurricular = int(
            request.form["extracurricular"]
        )


        # ====================================================
        # CREATE STUDENT DATA
        # ====================================================

        student_data = pd.DataFrame({

            "age": [age],

            "attendance": [attendance],

            "study_hours": [study_hours],

            "previous_score": [previous_score],

            "assignment_marks": [assignment_marks],

            "internal_marks": [internal_marks],

            "participation": [participation],


            "extracurricular": [extracurricular]

        })


        # ====================================================
        # ML PREDICTION
        # ====================================================

        predicted_score = model.predict(
            student_data
        )[0]


        # ====================================================
        # PERFORMANCE CATEGORY
        # ====================================================

        if predicted_score >= 85:

            category = "Excellent"

        elif predicted_score >= 70:

            category = "Good"

        elif predicted_score >= 50:

            category = "Average"

        else:

            category = "Needs Improvement"


        # ====================================================
        # RESULT PAGE
        # ====================================================

        return render_template(

            "result.html",

            name=name,

            score=round(
                predicted_score,
                2
            ),

            category=category,

            top_features=top_features

        )

    except Exception as e:

        return f"""
        <h2>Prediction Error</h2>
        <p>{str(e)}</p>
        <br>
        <a href="/">Go Back</a>
        """, 500


# ============================================================
# HEALTH CHECK API
# ============================================================

@app.route("/api/health")
def health_check():

    try:

        db.session.execute(
            text("SELECT 1")
        )

        database_status = "connected"

    except Exception as e:

        database_status = "disconnected"


    return {
        "status": "healthy",
        "database": database_status,
        "service": "ScoreVision"
    }


# ============================================================
# API INFORMATION
# ============================================================

@app.route("/api")
def api_info():

    return {
        "status": "success",
        "message": "ScoreVision API is running",
        "version": "1.0"
    }


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return {
        "status": "error",
        "error": "Resource Not Found"
    }, 404


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )