import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from database.db import db
from models.user import User

logger = logging.getLogger(__name__)

# Auth Blueprint for user authentication and authorization endpoints
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def auth_placeholder():
    """Placeholder endpoint for authentication API routes."""
    return jsonify({
        "status": "success",
        "message": "Auth API placeholder — user registration & authentication endpoints coming soon"
    }), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user in the ScoreVision system.

    Accepts JSON payload with name, email, password, and role.
    Validates input fields, checks for duplicate email, hashes password,
    persists user to database, and returns safe user dictionary (excl. password).
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        # 1. Validate required fields
        missing_fields = []
        for field, val in [("name", name), ("email", email), ("password", password), ("role", role)]:
            if val is None or not isinstance(val, str) or (field != "password" and not val.strip()) or (field == "password" and not val):
                missing_fields.append(field)

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        normalized_email = email.strip().lower()
        normalized_role = role.strip().lower()

        # 2. Validate role against allowed roles defined in User model
        if normalized_role not in User.ALLOWED_ROLES:
            return jsonify({
                "error": f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(User.ALLOWED_ROLES))}"
            }), 400

        # 3. Validate password complexity (minimum length check)
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400

        # 4. Check if email is already registered
        existing_user = User.query.filter_by(email=normalized_email).first()
        if existing_user:
            return jsonify({"error": "Email already registered"}), 409

        # 5. Create user object and hash password securely
        user = User(
            name=name.strip(),
            email=normalized_email,
            role=normalized_role
        )
        user.set_password(password)

        # 6. Save user to database
        db.session.add(user)
        db.session.commit()

        # 7. Return created user's safe info (to_dict excludes password_hash)
        return jsonify({
            "status": "success",
            "message": "User registered successfully",
            "user": user.to_dict()
        }), 201

    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during user registration: {str(e)}", exc_info=True)
        return jsonify({"error": "Something went wrong"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and issue a JWT access token.

    Accepts JSON payload with email and password.
    Returns HTTP 200 with JWT access_token on success, generic HTTP 401 on failure.
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Email and password are required"}), 400

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        normalized_email = email.strip().lower()

        # Search existing User by email
        user = User.query.filter_by(email=normalized_email).first()

        # Verify user exists and password is correct (generic message on fail)
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401

        # Generate JWT access token with safe claims (user_id, role)
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "user_id": user.id,
                "role": user.role
            }
        )

        # Return successful login details with access_token and safe user dict
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "access_token": access_token,
            "user": user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during user login: {str(e)}", exc_info=True)
        return jsonify({"error": "Something went wrong"}), 500


@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    """
    Protected API endpoint accessible only with a valid JWT Bearer token.
    Returns authenticated user identity and claims without exposing sensitive data.
    """
    current_user_id = get_jwt_identity()
    claims = get_jwt()

    return jsonify({
        "status": "success",
        "message": "Protected route accessed successfully",
        "user": {
            "user_id": claims.get("user_id", current_user_id),
            "role": claims.get("role")
        }
    }), 200

