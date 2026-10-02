from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
from database.db import db


class User(db.Model):
    """
    User model representing registered users in the ScoreVision system.
    Supports role-based authorization (student, faculty, admin) and secure
    password hashing using werkzeug.security.
    """
    __tablename__ = "users"

    # Allowed role definitions for RBAC security
    ALLOWED_ROLES = {"student", "faculty", "admin"}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __init__(self, name: str, email: str, role: str = "student", password: str = None):
        """Initialize User instance with validated role and optional password."""
        self.name = name.strip()
        self.email = email.strip().lower()
        self.role = self._validate_role_value(role)
        if password:
            self.set_password(password)

    @validates("role")
    def validate_role(self, key, role_value):
        """SQLAlchemy attribute validator for user role."""
        return self._validate_role_value(role_value)

    @classmethod
    def _validate_role_value(cls, role_value: str) -> str:
        """Utility method to enforce role restriction (student, faculty, admin)."""
        if not role_value or role_value.lower() not in cls.ALLOWED_ROLES:
            raise ValueError(
                f"Invalid role '{role_value}'. Allowed roles are: {', '.join(sorted(cls.ALLOWED_ROLES))}"
            )
        return role_value.lower()

    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password using werkzeug.security.
        Never stores plain-text passwords.
        """
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Check provided plain-text password against stored password hash.
        Returns True if password matches, False otherwise.
        """
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """
        Convert user object to dictionary for API JSON responses.
        Excludes sensitive information like password_hash.
        """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
