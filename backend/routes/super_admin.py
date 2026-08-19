from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models.user import User
from models.print_order import PrintOrder
from models.audit_log import AuditLog
from middleware.auth_required import role_required
from datetime import datetime, timezone
import uuid

super_admin_bp = Blueprint("super_admin", __name__)


# ── GET /api/super-admin/stats ───────────────────────────────────────────────
@super_admin_bp.route('/stats', methods=['GET'])
@role_required('super_admin')
def get_system_stats(current_user):
    """Return high-level system analytics for Super Admin."""
    all_users = User.query.all()
    total_users = len(all_users)
    customers = [u for u in all_users if u.role == 'customer']
    admins = [u for u in all_users if u.role == 'admin']
    super_admins = [u for u in all_users if u.role == 'super_admin']

    active_customers = sum(1 for u in customers if u.is_active)
    disabled_users = sum(1 for u in all_users if not u.is_active)
    total_logins = sum(u.login_count or 0 for u in all_users)
    users_logged_in_at_least_once = sum(1 for u in all_users if (u.login_count or 0) > 0)

    orders = PrintOrder.query.all()
    total_orders = len(orders)
    total_revenue = sum(o.total_price for o in orders if o.status in {'Accepted', 'Printing', 'Completed'})
    total_printed_pages = sum(o.printed_pages * o.copies for o in orders if o.status == 'Completed')

    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_customers": len(customers),
            "active_customers": active_customers,
            "disabled_users": disabled_users,
            "admin_count": len(admins),
            "admin_active": admins[0].is_active if admins else False,
            "total_logins": total_logins,
            "users_logged_in_count": users_logged_in_at_least_once,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "total_printed_pages": total_printed_pages,
        }
    }), 200


# ── GET /api/super-admin/users ───────────────────────────────────────────────
@super_admin_bp.route('/users', methods=['GET'])
@role_required('super_admin')
def list_users(current_user):
    """
    List all users with filtering and search.
    Supports query params: search, role, status (active|disabled).
    """
    search = request.args.get('search', '').strip().lower()
    role_filter = request.args.get('role', '').strip().lower()
    status_filter = request.args.get('status', '').strip().lower()

    query = User.query

    if role_filter:
        query = query.filter_by(role=role_filter)

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'disabled':
        query = query.filter_by(is_active=False)

    users = query.order_by(User.created_at.desc()).all()

    if search:
        users = [
            u for u in users
            if search in u.name.lower() or search in u.email.lower() or search in str(u.id).lower()
        ]

    return jsonify({
        "total": len(users),
        "users": [u.to_dict() for u in users]
    }), 200


# ── POST /api/super-admin/users ──────────────────────────────────────────────
@super_admin_bp.route('/users', methods=['POST'])
@role_required('super_admin')
def create_customer_account(current_user):
    """
    Super Admin manually adds a new Customer account.
    Strictly restricted to creating 'customer' accounts.
    """
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "A user with this email already exists."}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    now = datetime.now(timezone.utc)

    user = User(
        name=name,
        email=email,
        password_hash=pw_hash,
        role="customer",
        is_active=True,
        last_login=None,
        login_count=0,
    )
    db.session.add(user)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="SUPERADMIN_CREATED_CUSTOMER",
        user=current_user,
        details=f"Super Admin created customer: {email} ({name})",
        ip_address=ip_addr,
    )

    return jsonify({
        "message": "Customer account created successfully.",
        "user": user.to_dict()
    }), 201


# ── PATCH /api/super-admin/users/<user_id>/status ───────────────────────────
@super_admin_bp.route('/users/<user_id>/status', methods=['PATCH'])
@role_required('super_admin')
def toggle_user_status(current_user, user_id):
    """Enable or disable a user account."""
    if str(current_user.id) == str(user_id):
        return jsonify({"error": "You cannot disable your own Super Admin account."}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    else:
        user.is_active = not user.is_active

    db.session.commit()

    action_label = "ENABLED" if user.is_active else "DISABLED"
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action=f"USER_{action_label}",
        user=current_user,
        details=f"User {user.email} (Role: {user.role}) was {action_label.lower()} by Super Admin",
        ip_address=ip_addr,
    )

    return jsonify({
        "message": f"User account has been {'enabled' if user.is_active else 'disabled'}.",
        "user": user.to_dict()
    }), 200


# ── DELETE /api/super-admin/users/<user_id> ──────────────────────────────────
@super_admin_bp.route('/users/<user_id>', methods=['DELETE'])
@role_required('super_admin')
def delete_customer(current_user, user_id):
    """
    Delete a customer account.
    Admin or Super Admin accounts cannot be deleted via this endpoint.
    Historical print records are preserved safely (user_id set null, customer name/email snapshot retained).
    """
    if str(current_user.id) == str(user_id):
        return jsonify({"error": "You cannot delete your own Super Admin account."}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role != 'customer':
        return jsonify({"error": f"Cannot delete '{user.role}' account via customer management endpoint."}), 400

    user_email = user.email
    user_name = user.name

    # Detach print orders so historical print records are preserved with snapshots
    orders = PrintOrder.query.filter_by(user_id=user.id).all()
    for order in orders:
        if not order.customer_name:
            order.customer_name = user_name
        if not order.customer_email:
            order.customer_email = user_email
        order.user_id = None

    db.session.delete(user)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="CUSTOMER_DELETED",
        user=current_user,
        details=f"Customer {user_email} deleted by Super Admin. ({len(orders)} historical print records preserved)",
        ip_address=ip_addr,
    )

    return jsonify({
        "message": f"Customer account {user_email} deleted successfully. Historical print records were preserved."
    }), 200


# ── GET /api/super-admin/admin-account ───────────────────────────────────────
@super_admin_bp.route('/admin-account', methods=['GET'])
@role_required('super_admin')
def get_admin_account(current_user):
    """Retrieve details for the single Admin account."""
    admin = User.query.filter_by(role='admin').first()
    return jsonify({
        "admin": admin.to_dict() if admin else None
    }), 200


# ── POST /api/super-admin/admin-account/replace ──────────────────────────────
@super_admin_bp.route('/admin-account/replace', methods=['POST'])
@role_required('super_admin')
def replace_or_create_admin(current_user):
    """
    Create or replace the single Admin account.
    Strictly guarantees at most 1 Admin exists.
    If an existing Admin exists, updates their credentials/profile.
    If no Admin exists, creates a fresh Admin.
    """
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required for the Admin account."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    # Check if this email is already used by a non-admin user
    existing_user_with_email = User.query.filter_by(email=email).first()
    admin = User.query.filter_by(role='admin').first()

    if existing_user_with_email and (not admin or existing_user_with_email.id != admin.id):
        return jsonify({"error": "This email address is already in use by another account."}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    now = datetime.now(timezone.utc)

    if admin:
        old_email = admin.email
        admin.name = name
        admin.email = email
        admin.password_hash = pw_hash
        admin.is_active = True
        admin.updated_at = now
        action_msg = f"Replaced Admin account (previous: {old_email}, new: {email})"
    else:
        admin = User(
            name=name,
            email=email,
            password_hash=pw_hash,
            role="admin",
            is_active=True,
            last_login=None,
            login_count=0,
        )
        db.session.add(admin)
        action_msg = f"Created single Admin account ({email})"

    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="ADMIN_ACCOUNT_CONFIGURED",
        user=current_user,
        details=action_msg,
        ip_address=ip_addr,
    )

    return jsonify({
        "message": "Admin account successfully configured.",
        "admin": admin.to_dict()
    }), 200


# ── POST /api/super-admin/admin-account/reset-password ───────────────────────
@super_admin_bp.route('/admin-account/reset-password', methods=['POST'])
@role_required('super_admin')
def reset_admin_password(current_user):
    """Super Admin resets the single Admin password."""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        return jsonify({"error": "No Admin account currently exists."}), 404

    data = request.get_json(silent=True) or {}
    new_password = str(data.get('password', ''))

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    admin.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    admin.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="ADMIN_PASSWORD_RESET",
        user=current_user,
        details=f"Super Admin reset password for Admin ({admin.email})",
        ip_address=ip_addr,
    )

    return jsonify({"message": f"Password for Admin ({admin.email}) has been reset successfully."}), 200


# ── PATCH /api/super-admin/admin-account/status ──────────────────────────────
@super_admin_bp.route('/admin-account/status', methods=['PATCH'])
@role_required('super_admin')
def toggle_admin_status(current_user):
    """Enable or disable the single Admin account."""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        return jsonify({"error": "No Admin account currently exists."}), 404

    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        admin.is_active = bool(data['is_active'])
    else:
        admin.is_active = not admin.is_active

    db.session.commit()

    action_label = "ENABLED" if admin.is_active else "DISABLED"
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action=f"ADMIN_{action_label}",
        user=current_user,
        details=f"Admin account ({admin.email}) was {action_label.lower()} by Super Admin",
        ip_address=ip_addr,
    )

    return jsonify({
        "message": f"Admin account has been {'enabled' if admin.is_active else 'disabled'}.",
        "admin": admin.to_dict()
    }), 200


# ── DELETE /api/super-admin/admin-account ────────────────────────────────────
@super_admin_bp.route('/admin-account', methods=['DELETE'])
@role_required('super_admin')
def delete_admin_account(current_user):
    """
    Remove the current Admin account.
    Allows Super Admin to create a fresh one afterwards.
    Preserves all historical print records.
    """
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        return jsonify({"error": "No Admin account currently exists to delete."}), 404

    admin_email = admin.email
    db.session.delete(admin)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="ADMIN_ACCOUNT_DELETED",
        user=current_user,
        details=f"Admin account ({admin_email}) was deleted by Super Admin",
        ip_address=ip_addr,
    )

    return jsonify({"message": f"Admin account ({admin_email}) deleted. You may now create a new Admin account."}), 200


# ── GET /api/super-admin/audit-logs ──────────────────────────────────────────
@super_admin_bp.route('/audit-logs', methods=['GET'])
@role_required('super_admin')
def list_audit_logs(current_user):
    """List recent activity & audit logs."""
    limit = min(int(request.args.get('limit', 100)), 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({
        "logs": [l.to_dict() for l in logs]
    }), 200
