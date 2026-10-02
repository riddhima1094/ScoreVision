from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import logging

from database.db import db
from models.user import User
from models.academic_record import AcademicRecord
from models.prediction import Prediction

from utils.decorators import role_required
from routes.prediction import predict_performance

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@dashboard_bp.route("/student", methods=["GET"])
@jwt_required()
@role_required("student")
def student_dashboard():

    try:

        current_user_id = int(get_jwt_identity())

        records = AcademicRecord.query.filter_by(
            user_id=current_user_id
        ).order_by(
            AcademicRecord.created_at.desc()
        ).all()

        if not records:
            return jsonify({
                "status": "success",
                "message": "No academic records found for this student.",
                "data": []
            }), 200

        dashboard_data = []

        for record in records:

            rec_dict = record.to_dict()

            rec_dict["predicted_score"] = predict_performance(record)

            dashboard_data.append(rec_dict)

        return jsonify({
            "status": "success",
            "message": "Student dashboard data retrieved successfully",
            "data": dashboard_data
        }), 200

    except Exception as e:

        logger.error(
            f"Student dashboard error: {str(e)}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "An unexpected error occurred"
        }), 500


# ============================================================
# ADMIN / FACULTY DASHBOARD SUMMARY
# ============================================================

@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
@role_required("faculty", "admin")
def dashboard_summary():

    try:

        # ----------------------------------------------------
        # TOTAL REGISTERED STUDENTS
        # ----------------------------------------------------

        total_students = User.query.filter_by(
            role="student"
        ).count()


        # ----------------------------------------------------
        # TOTAL PREDICTIONS
        # ----------------------------------------------------

        total_predictions = Prediction.query.count()


        # ----------------------------------------------------
        # PREDICTION STATISTICS
        # ----------------------------------------------------

        predictions = Prediction.query.all()

        total_predicted_score = 0.0
        passing_count = 0
        failing_count = 0

        for prediction in predictions:

            score = float(
                prediction.predicted_score or 0
            )

            total_predicted_score += score

            if score >= 40:
                passing_count += 1
            else:
                failing_count += 1


        # ----------------------------------------------------
        # AVERAGE SCORE
        # ----------------------------------------------------

        if total_predictions > 0:

            average_score = round(
                total_predicted_score / total_predictions,
                2
            )

        else:

            average_score = 0.0


        # ----------------------------------------------------
        # PASS RATE
        # ----------------------------------------------------

        if total_predictions > 0:

            pass_rate = round(
                (passing_count / total_predictions) * 100,
                2
            )

        else:

            pass_rate = 0.0


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "status": "success",

            "message": "Dashboard summary retrieved successfully",

            "data": {

                "total_students":
                    total_students,

                "total_students_with_records":
                    AcademicRecord.query.with_entities(
                        AcademicRecord.user_id
                    ).distinct().count(),

                "total_predictions_made":
                    total_predictions,

                "average_predicted_score":
                    average_score,

                "passing_predictions_count":
                    passing_count,

                "failing_predictions_count":
                    failing_count,

                "pass_rate":
                    pass_rate,

                "pass_threshold":
                    40.0

            }

        }), 200


    except Exception as e:

        logger.error(
            f"Dashboard summary error: {str(e)}",
            exc_info=True
        )

        return jsonify({

            "status": "error",

            "error":
                "An unexpected error occurred"

        }), 500


# ============================================================
# GENERIC DASHBOARD ROUTER
# ============================================================

@dashboard_bp.route("", methods=["GET"])
@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def dashboard_router():

    claims = get_jwt()

    role = claims.get(
        "role",
        ""
    ).lower()


    if role == "student":

        return student_dashboard()


    elif role in ["faculty", "admin"]:

        return dashboard_summary()


    else:

        return jsonify({

            "status": "error",

            "error":
                "Forbidden: Insufficient permissions"

        }), 403