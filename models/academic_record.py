from datetime import datetime, timezone
from sqlalchemy.orm import validates
from database.db import db


class AcademicRecord(db.Model):
    """
    AcademicRecord model storing student features for future ML performance prediction.
    Enforces strict data boundaries to ensure data quality before DB insertion.
    """
    __tablename__ = "academic_records"

    # Allowed categories for extracurricular involvement
    ALLOWED_EXTRACURRICULAR = {"none", "low", "medium", "high"}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    attendance_percentage = db.Column(db.Float, nullable=False)
    study_hours = db.Column(db.Float, nullable=False)
    previous_exam_score = db.Column(db.Float, nullable=False)
    assignment_marks = db.Column(db.Float, nullable=False)
    internal_assessment_marks = db.Column(db.Float, nullable=False)
    class_participation = db.Column(db.Float, nullable=False)
    sleep_hours = db.Column(db.Float, nullable=True, default=7.0)
    extracurricular_involvement = db.Column(db.String(20), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to User model (optional but good practice for SQLAlchemy)
    user = db.relationship('User', backref=db.backref('academic_records', lazy=True))

    def __init__(self, user_id: int, attendance_percentage: float, study_hours: float,
                 previous_exam_score: float, assignment_marks: float,
                 internal_assessment_marks: float, class_participation: float,
                 extracurricular_involvement: str, sleep_hours: float = 7.0):
        self.user_id = user_id
        # Use property setters / validates to enforce rules
        self.attendance_percentage = attendance_percentage
        self.study_hours = study_hours
        self.previous_exam_score = previous_exam_score
        self.assignment_marks = assignment_marks
        self.internal_assessment_marks = internal_assessment_marks
        self.class_participation = class_participation
        self.sleep_hours = sleep_hours
        self.extracurricular_involvement = extracurricular_involvement

    @validates("attendance_percentage", "previous_exam_score", "assignment_marks", "internal_assessment_marks", "class_participation")
    def validate_percentage(self, key, value):
        """Validate that percentage and marks fields are between 0 and 100."""
        try:
            val = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a number.")
        if not (0.0 <= val <= 100.0):
            raise ValueError(f"{key} must be between 0 and 100. Received: {value}")
        return val

    @validates("study_hours")
    def validate_hours(self, key, value):
        """Validate that hours fields are non-negative."""
        try:
            val = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a number.")
        if val < 0.0:
            raise ValueError(f"{key} cannot be negative. Received: {value}")
        return val

    @validates("extracurricular_involvement")
    def validate_extracurricular(self, key, value):
        """Validate extracurricular involvement against allowed categorical values."""
        if not value or str(value).strip().lower() not in self.ALLOWED_EXTRACURRICULAR:
            allowed = ", ".join(sorted(self.ALLOWED_EXTRACURRICULAR))
            raise ValueError(f"Invalid {key} '{value}'. Allowed values are: {allowed}")
        return str(value).strip().lower()

    def to_dict(self) -> dict:
        """Convert academic record object to dictionary for API JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "attendance_percentage": self.attendance_percentage,
            "study_hours": self.study_hours,
            "previous_exam_score": self.previous_exam_score,
            "assignment_marks": self.assignment_marks,
            "internal_assessment_marks": self.internal_assessment_marks,
            "class_participation": self.class_participation,
            "sleep_hours": self.sleep_hours,
            "extracurricular_involvement": self.extracurricular_involvement,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AcademicRecord id={self.id} user_id={self.user_id}>"
