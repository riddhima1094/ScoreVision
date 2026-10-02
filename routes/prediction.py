import os
import joblib
import pandas as pd
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import logging
from database.db import db
from models.academic_record import AcademicRecord
from models.prediction import Prediction

logger = logging.getLogger(__name__)

# Prediction Blueprint for ML model inference and student score prediction endpoints
prediction_bp = Blueprint("prediction", __name__)

# Load ML Model
ml_model = None
try:
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _model_path = os.path.join(_base_dir, "model", "scorevision_model.pkl")
    if os.path.exists(_model_path):
        ml_model = joblib.load(_model_path)
        logger.info(f"ML Model loaded successfully from {_model_path}")
except Exception as _e:
    logger.warning(f"Could not load ML model: {_e}")


def calculate_dummy_score(record: AcademicRecord) -> float:
    """Helper function to calculate the formula-based score fallback."""
    attendance_score = float(record.attendance_percentage) * 0.20
    prev_score = float(record.previous_exam_score) * 0.30
    assignment_score = float(record.assignment_marks) * 0.15
    internal_score = float(record.internal_assessment_marks) * 0.15
    participation_score = float(record.class_participation) * 0.10
    study_score = min(float(record.study_hours) * 10, 100) * 0.10
    
    predicted_score = attendance_score + prev_score + assignment_score + internal_score + participation_score + study_score
    
    bonus = 0
    if record.extracurricular_involvement == "high":
        bonus += 2
    elif record.extracurricular_involvement == "medium":
        bonus += 1
        
    if 6 <= float(record.sleep_hours) <= 9:
        bonus += 2
        
    predicted_score += bonus
    return min(round(predicted_score, 2), 100.0)


def predict_performance(record: AcademicRecord, age: float = 20.0) -> float:
    """Predict student score using trained ML model if available, fallback to formula."""
    if ml_model is not None:
        try:
            extra_val = 1 if str(record.extracurricular_involvement).strip().lower() in ["low", "medium", "high", "1", "yes", "true"] else 0
            df = pd.DataFrame([{
                "age": float(age),
                "attendance": float(record.attendance_percentage),
                "study_hours": float(record.study_hours),
                "previous_score": float(record.previous_exam_score),
                "assignment_marks": float(record.assignment_marks),
                "internal_marks": float(record.internal_assessment_marks),
                "participation": float(record.class_participation),
                "sleep_hours": float(record.sleep_hours),
                "extracurricular": extra_val
            }])
            score = float(ml_model.predict(df)[0])
            return min(max(round(score, 2), 0.0), 100.0)
        except Exception as e:
            logger.warning(f"ML prediction failed, falling back: {e}")
    return calculate_dummy_score(record)


def get_performance_category(score: float) -> str:
    """Helper to determine performance category based on score."""
    if score >= 75.0:
        return "Good"
    elif score >= 50.0:
        return "Average"
    else:
        return "Poor"


@prediction_bp.route("/predict/<int:record_id>", methods=["GET"])
@jwt_required()
def predict_score(record_id):
    """
    Prediction endpoint using the trained Random Forest ML model.
    """
    try:
        current_user_id = get_jwt_identity()
        record = AcademicRecord.query.filter_by(id=record_id, user_id=int(current_user_id)).first()
        
        if not record:
            return jsonify({"error": "Academic record not found or access denied"}), 404
            
        predicted_score = predict_performance(record)
        return jsonify({
            "status": "success",
            "message": "Prediction generated using ML model",
            "data": {
                "record_id": record.id,
                "predicted_score": predicted_score,
                "model_used": "RandomForestRegressor" if ml_model is not None else "formula_fallback"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@prediction_bp.route("/predict", methods=["POST"])
@jwt_required()
def trigger_prediction():
    """
    Trigger an ML prediction for a specific record_id or the latest record if none provided.
    Saves the result to Prediction history.
    """
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        record_id = data.get("record_id")

        if record_id:
            record = AcademicRecord.query.filter_by(id=record_id, user_id=current_user_id).first()
        else:
            record = AcademicRecord.query.filter_by(user_id=current_user_id).order_by(AcademicRecord.created_at.desc()).first()

        if not record:
            return jsonify({"error": "Academic record not found or access denied"}), 404

        predicted_score = predict_performance(record)
        category = get_performance_category(predicted_score)

        prediction_result = Prediction(
            user_id=current_user_id,
            record_id=record.id,
            predicted_score=predicted_score,
            category=category
        )
        db.session.add(prediction_result)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Prediction generated and saved successfully",
            "data": prediction_result.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during POST prediction: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@prediction_bp.route("/history/<int:prediction_id>", methods=["DELETE"])
@jwt_required()
def delete_prediction(prediction_id):
    """
    Delete a specific prediction from history.
    Students can delete their own predictions; faculty/admin can delete any.
    """
    try:
        current_user_id = int(get_jwt_identity())
        role = get_jwt().get("role", "student").lower()

        if role in ["faculty", "admin"]:
            prediction = Prediction.query.get_or_404(prediction_id)
        else:
            prediction = Prediction.query.filter_by(id=prediction_id, user_id=current_user_id).first_or_404()

        db.session.delete(prediction)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Prediction deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting prediction: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete prediction"}), 500


@prediction_bp.route("/history", methods=["GET"])
@jwt_required()
def get_prediction_history():
    """
    Returns the authenticated student's past predictions, most recent first.
    """
    try:
        current_user_id = int(get_jwt_identity())
        predictions = Prediction.query.filter_by(user_id=current_user_id).order_by(Prediction.created_at.desc()).all()
        
        return jsonify({
            "status": "success",
            "data": [p.to_dict() for p in predictions]
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving prediction history: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@prediction_bp.route("/academic", methods=["POST"])
@jwt_required()
def create_academic_record():
    """
    Protected endpoint to create a new academic record for the authenticated user.
    Validates input features securely before insertion.
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        current_user_id = get_jwt_identity()

        # Extract features
        attendance = data.get("attendance_percentage")
        study = data.get("study_hours")
        prev_score = data.get("previous_exam_score")
        assignments = data.get("assignment_marks")
        internal = data.get("internal_assessment_marks")
        participation = data.get("class_participation")
        sleep = data.get("sleep_hours")
        extracurricular = data.get("extracurricular_involvement")

        # Validate that all required fields are present
        required_fields = [
            ("attendance_percentage", attendance),
            ("study_hours", study),
            ("previous_exam_score", prev_score),
            ("assignment_marks", assignments),
            ("internal_assessment_marks", internal),
            ("class_participation", participation),
            ("sleep_hours", sleep),
            ("extracurricular_involvement", extracurricular)
        ]

        missing_fields = [f[0] for f in required_fields if f[1] is None or str(f[1]).strip() == ""]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Create record (Validation rules in the model will enforce boundaries)
        record = AcademicRecord(
            user_id=int(current_user_id),
            attendance_percentage=attendance,
            study_hours=study,
            previous_exam_score=prev_score,
            assignment_marks=assignments,
            internal_assessment_marks=internal,
            class_participation=participation,
            sleep_hours=sleep,
            extracurricular_involvement=extracurricular
        )

        db.session.add(record)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Academic record created successfully",
            "data": record.to_dict()
        }), 201

    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating academic record: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@prediction_bp.route("/academic", methods=["GET"])
@jwt_required()
def get_academic_records():
    """
    Protected endpoint to retrieve all academic records for the authenticated user.
    Ensures strict data isolation (users cannot fetch others' records).
    """
    try:
        current_user_id = get_jwt_identity()

        # Fetch records belonging ONLY to the authenticated user
        records = AcademicRecord.query.filter_by(user_id=int(current_user_id)).all()

        return jsonify({
            "status": "success",
            "data": [r.to_dict() for r in records]
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error retrieving academic records: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


@prediction_bp.route("/academic/<int:record_id>", methods=["DELETE"])
@jwt_required()
def delete_academic_record(record_id):
    """
    Delete an academic record and its associated predictions.
    Students can delete their own; faculty/admin can delete any.
    """
    try:
        current_user_id = int(get_jwt_identity())
        role = get_jwt().get("role", "student").lower()

        if role in ["faculty", "admin"]:
            record = AcademicRecord.query.get_or_404(record_id)
        else:
            record = AcademicRecord.query.filter_by(id=record_id, user_id=current_user_id).first_or_404()

        # Delete dependent predictions first
        Prediction.query.filter_by(record_id=record.id).delete(synchronize_session=False)
        db.session.delete(record)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Academic record deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting academic record: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete academic record"}), 500

