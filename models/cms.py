from datetime import datetime, timezone
from database.db import db


class Lecture(db.Model):
    __tablename__ = "lectures"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=False)
    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    faculty = db.relationship(
        "User",
        backref=db.backref("lectures_created", lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "faculty_id": self.faculty_id,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }

class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    duration_minutes = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    faculty = db.relationship(
        "User",
        backref=db.backref("tests_created", lazy=True)
    )

    # Questions
    questions = db.relationship(
        "Question",
        backref="test",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # Submissions
    submissions = db.relationship(
        "TestSubmission",
        back_populates="test",
        lazy=True,
        cascade="all, delete-orphan"
    )
    def to_dict(self, include_questions=False, include_answers=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "faculty_id": self.faculty_id,
            "duration_minutes": self.duration_minutes,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "questions_count": len(self.questions)
        }

        if include_questions:
            data["questions"] = [
                q.to_dict(include_answer=include_answers)
                for q in self.questions
            ]

        return data
    
class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id"),
        nullable=False
    )

    question_text = db.Column(db.Text, nullable=False)

    option_a = db.Column(
        db.String(255),
        nullable=False
    )

    option_b = db.Column(
        db.String(255),
        nullable=False
    )

    option_c = db.Column(
        db.String(255),
        nullable=False
    )

    option_d = db.Column(
        db.String(255),
        nullable=False
    )

    correct_option = db.Column(
        db.String(1),
        nullable=False
    )

    def to_dict(self, include_answer=False):
        data = {
            "id": self.id,
            "test_id": self.test_id,
            "question_text": self.question_text,
            "options": {
                "A": self.option_a,
                "B": self.option_b,
                "C": self.option_c,
                "D": self.option_d
            }
        }

        if include_answer:
            data["correct_option"] = self.correct_option

        return data

class TestSubmission(db.Model):
    __tablename__ = "test_submissions"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    score = db.Column(db.Float, nullable=False)

    total_questions = db.Column(
        db.Integer,
        nullable=False
    )

    is_faculty_overridden = db.Column(
        db.Boolean,
        default=False
    )

    submitted_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "test_submissions",
            lazy=True
        )
    )

    test = db.relationship(
        "Test",
        back_populates="submissions"
    )

    def to_dict(self):
        percentage = 0

        if self.total_questions > 0:
            percentage = round(
                (self.score / self.total_questions) * 100,
                2
            )

        return {
            "id": self.id,
            "test_id": self.test_id,
            "test_title": (
                self.test.title
                if self.test else "Unknown Test"
            ),
            "user_id": self.user_id,
            "score": self.score,
            "total_questions": self.total_questions,
            "percentage": percentage,
            "is_faculty_overridden": self.is_faculty_overridden,
            "submitted_at": (
                self.submitted_at.isoformat()
                if self.submitted_at else None
            )
        }
