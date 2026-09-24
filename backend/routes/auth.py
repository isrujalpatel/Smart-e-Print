from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models.user import User
from models.audit_log import AuditLog
from middleware.auth_required import token_required
from config import Config
import jwt
from datetime import datetime, timezone, timedelta
import urllib.request
import json as json_lib

auth_bp = Blueprint("auth", __name__)


# ── POST /api/auth/register ──────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Public registration endpoint.
    STRICT RULE: Only 'customer' accounts can be created via public registration.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    # Validate required fields
    for field in ("name", "email", "password"):
        if not str(data.get(field, "")).strip():
            return jsonify({"error": f"{field.capitalize()} is required."}), 400

    name     = str(data["name"]).strip()
    email    = str(data["email"]).strip().lower()
    password = str(data["password"])

    # Strict check: Public registration is ONLY for customers
    requested_role = str(data.get("role", "customer")).strip().lower()
    if requested_role in ("admin", "super_admin", "owner"):
        return jsonify({
            "error": "Administrative accounts cannot be registered publicly."
        }), 403

    role = "customer"

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    now = datetime.now(timezone.utc)

    user = User(
        name=name,
        email=email,
        password_hash=pw_hash,
        role=role,
        is_active=True,
        last_login=now,
        login_count=1,
    )
    db.session.add(user)
    db.session.commit()

    # Log audit event
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="CUSTOMER_REGISTERED",
        user=user,
        details=f"Customer registered with email: {email}",
        ip_address=ip_addr,
    )

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

    email    = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        return jsonify({
            "error": "Your account has been deactivated. Please contact an administrator."
        }), 403

    # Update login activity records
    user.last_login = datetime.now(timezone.utc)
    user.login_count = (user.login_count or 0) + 1
    db.session.commit()

    # Record login audit log
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="USER_LOGIN",
        user=user,
        details=f"Successful login (Role: {user.role})",
        ip_address=ip_addr,
    )

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


# ── PATCH /api/auth/profile/name ─────────────────────────────────────────────
@auth_bp.route("/profile/name", methods=["PATCH"])
@token_required
def update_name(current_user):
    """Update the current user's display name."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    new_name = str(data.get("name", "")).strip()
    if not new_name or len(new_name) < 2:
        return jsonify({"error": "Name must be at least 2 characters."}), 400
    if len(new_name) > 100:
        return jsonify({"error": "Name must be 100 characters or fewer."}), 400

    old_name = current_user.name
    current_user.name = new_name
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="PROFILE_NAME_UPDATED",
        user=current_user,
        details=f"Name changed from '{old_name}' to '{new_name}'",
        ip_address=ip_addr,
    )

    return jsonify({
        "message": "Name updated successfully.",
        "user": current_user.to_dict()
    }), 200


# ── POST /api/auth/profile/password ──────────────────────────────────────────
@auth_bp.route("/profile/password", methods=["POST"])
@token_required
def change_password(current_user):
    """Change the current user's password (requires current password)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    current_pw = str(data.get("current_password", ""))
    new_pw = str(data.get("new_password", ""))
    confirm_pw = str(data.get("confirm_password", ""))

    if not current_pw:
        return jsonify({"error": "Current password is required."}), 400
    if not new_pw or len(new_pw) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400
    if new_pw != confirm_pw:
        return jsonify({"error": "New passwords do not match."}), 400

    # Google-only users don't have a password
    if not current_user.password_hash:
        return jsonify({"error": "Your account uses Google sign-in and has no password to change."}), 400

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        return jsonify({"error": "Current password is incorrect."}), 401

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="PASSWORD_CHANGED",
        user=current_user,
        details="User changed their password",
        ip_address=ip_addr,
    )

    return jsonify({"message": "Password changed successfully."}), 200


# ── POST /api/auth/logout ────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user):
    """Acknowledge logout."""
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="USER_LOGOUT",
        user=current_user,
        details="User signed out",
        ip_address=ip_addr,
    )
    return jsonify({"message": "Logged out successfully."}), 200


# ── POST /api/auth/google ────────────────────────────────────────────────────
@auth_bp.route("/google", methods=["POST"])
def google_auth():
    """Verify a Google ID token and return a Smart e-Print JWT."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    credential = str(data.get("credential", "")).strip()
    if not credential:
        return jsonify({"error": "Google credential is required."}), 400

    # ── Verify token with Google's tokeninfo endpoint ─────────────────────────
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            gdata = json_lib.loads(resp.read().decode())
    except Exception:
        return jsonify({"error": "Failed to verify Google token. Please try again."}), 401

    if gdata.get("aud") != Config.GOOGLE_CLIENT_ID:
        return jsonify({"error": "Invalid token audience."}), 401

    google_id = gdata.get("sub", "")
    email     = str(gdata.get("email", "")).lower()
    name      = gdata.get("name") or email.split("@")[0]

    if not email or not google_id:
        return jsonify({"error": "Could not retrieve profile from Google."}), 401

    # ── Find or create user ───────────────────────────────────────────────────
    user = User.query.filter_by(email=email).first()
    now = datetime.now(timezone.utc)

    if user:
        if not user.is_active:
            return jsonify({
                "error": "Your account has been deactivated. Please contact an administrator."
            }), 403

        if not user.google_id:
            user.google_id = google_id
        user.last_login = now
        user.login_count = (user.login_count or 0) + 1
        db.session.commit()
    else:
        # Brand-new Google user — STRICTLY create as customer
        user = User(
            name=name,
            email=email,
            password_hash=None,
            role="customer",
            is_active=True,
            google_id=google_id,
            last_login=now,
            login_count=1,
        )
        db.session.add(user)
        db.session.commit()

        ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
        AuditLog.log(
            action="CUSTOMER_REGISTERED_GOOGLE",
            user=user,
            details=f"Customer registered via Google OAuth: {email}",
            ip_address=ip_addr,
        )

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="USER_LOGIN_GOOGLE",
        user=user,
        details="Google sign-in login",
        ip_address=ip_addr,
    )

    token = _generate_token(user)
    return jsonify({
        "message": "Google sign-in successful!",
        "token":   token,
        "user":    user.to_dict(),
    }), 200


# ── Helper ───────────────────────────────────────────────────────────────────
def _generate_token(user: User) -> str:
    """Encode a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=Config.JWT_EXPIRATION_HOURS)

    payload = {
        "user_id": str(user.id),
        "email":   user.email,
        "role":    user.role,
        "iat":     int(now.timestamp()),
        "exp":     int(expiry.timestamp()),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
