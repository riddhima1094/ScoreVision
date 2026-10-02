from datetime import datetime, timezone
from database.db import db

class Prediction(db.Model):
    """
    Prediction model storing the result of a prediction for a student's academic record.
    """
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    record_id = db.Column(db.Integer, db.ForeignKey('academic_records.id'), nullable=False)
    
    predicted_score = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('predictions', lazy=True))
    record = db.relationship('AcademicRecord', backref=db.backref('predictions', lazy=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "record_id": self.record_id,
            "predicted_score": self.predicted_score,
            "category": self.category,
            "date": self.created_at.isoformat() if self.created_at else None,
        }
