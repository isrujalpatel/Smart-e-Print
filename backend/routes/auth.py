from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models.user import User
from middleware.auth_required import token_required
from config import Config
import jwt
import datetime

auth_bp = Blueprint("auth", __name__)

ALLOWED_ROLES = {"customer", "owner"}


# ── POST /api/auth/register ──────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user and return a JWT token."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    # Validate required fields
    for field in ("name", "email", "password", "role"):
        if not data.get(field, "").strip():
            return jsonify({"error": f"{field.capitalize()} is required."}), 400

    name     = data["name"].strip()
    email    = data["email"].strip().lower()
    password = data["password"]
    role     = data["role"].strip().lower()

    if role not in ALLOWED_ROLES:
        return jsonify({"error": "Role must be 'customer' or 'owner'."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(name=name, email=email, password_hash=pw_hash, role=role)
    db.session.add(user)
    db.session.commit()

    token = _generate_token(user)
    return jsonify({
        "message": "Account created successfully!",
        "token":   token,
        "user":    user.to_dict(),
    }), 201


# ── POST /api/auth/login ─────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate with email + password and return a JWT token."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401

    token = _generate_token(user)
    return jsonify({
        "message": "Login successful!",
        "token":   token,
        "user":    user.to_dict(),
    }), 200


# ── GET /api/auth/me ─────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@token_required
def get_me(current_user):
    """Return the current authenticated user's profile."""
    return jsonify({"user": current_user.to_dict()}), 200


# ── POST /api/auth/logout ────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user):
    """
    Acknowledge logout.
    JWT is stateless — actual token removal happens on the client side.
    """
    return jsonify({"message": "Logged out successfully."}), 200


# ── Helper ───────────────────────────────────────────────────────────────────
def _generate_token(user: User) -> str:
    """Encode a signed JWT for the given user."""
    now = datetime.datetime.utcnow()
    expiry = now + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": str(user.id),  # Convert UUID to string
        "email":   user.email,
        "role":    user.role,
        "iat":     int(now.timestamp()),  # Convert datetime to Unix timestamp
        "exp":     int(expiry.timestamp()),  # Convert datetime to Unix timestamp
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
