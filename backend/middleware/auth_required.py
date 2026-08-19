from flask import request, jsonify
from functools import wraps
import jwt
from config import Config
from extensions import db
from models.user import User


def token_required(f):
    """
    Decorator — protects a route by verifying the JWT Bearer token.
    Checks that the user exists and is active.
    Injects `current_user` (User model instance) as the first argument.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

        if not token:
            return jsonify({"error": "Authorization token is missing."}), 401

        try:
            payload = jwt.decode(
                token, Config.JWT_SECRET_KEY, algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            if not user_id:
                return jsonify({"error": "Invalid token payload."}), 401

            current_user = db.session.get(User, user_id)
            if not current_user:
                return jsonify({"error": "User not found or account removed."}), 401

            if not current_user.is_active:
                return jsonify({"error": "Your account has been deactivated. Please contact an administrator."}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired. Please login again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please login again."}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def role_required(*roles):
    """
    Decorator — restricts access to specific roles.
    Must be used with token_required or standalone (invokes token_required internally).

    Usage:
        @bp.route('/super-secret')
        @role_required('super_admin')
        def super_secret_endpoint(current_user):
            ...
    """
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return jsonify({
                    "error": f"Access denied. Required role: {', '.join(roles)}."
                }), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator
