from flask import request, jsonify
from functools import wraps
import jwt
from config import Config
from models.user import User


def token_required(f):
    """
    Decorator — protects a route by verifying the JWT Bearer token.
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
            current_user = User.query.get(payload.get("user_id"))
            if not current_user:
                return jsonify({"error": "User not found."}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired. Please login again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please login again."}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def role_required(*roles):
    """
    Decorator — restricts access to specific roles.
    Must be used AFTER @token_required on the same route,
    or call it standalone (it calls token_required internally).

    Usage:
        @auth_bp.route('/owner-only')
        @role_required('owner')
        def owner_only_endpoint(current_user):
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
