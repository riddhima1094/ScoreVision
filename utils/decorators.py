from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt


def role_required(*allowed_roles):
    """
    Decorator to verify JWT authentication and enforce role-based authorization.

    Usage:
        @auth_bp.route("/student-only")
        @role_required("student")
        def student_route():
            ...

        @auth_bp.route("/admin-only")
        @role_required("admin")
        def admin_route():
            ...

    First verifies that a valid JWT token is present (HTTP 401 on missing/invalid token),
    then checks whether the authenticated user's role matches any of the allowed roles.
    Returns HTTP 403 Forbidden if the user role is unauthorized.
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get("role")
            normalized_allowed = [r.lower() for r in allowed_roles]

            if not user_role or user_role.lower() not in normalized_allowed:
                return jsonify({
                    "error": "Forbidden: Insufficient permissions for this resource"
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
