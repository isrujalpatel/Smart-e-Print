from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import traceback
from datetime import datetime, timezone
from config import Config
from extensions import db, bcrypt
from routes.auth import auth_bp
from routes.orders import orders_bp
from routes.super_admin import super_admin_bp
from models.user import User
from models.print_order import PrintOrder
from models.audit_log import AuditLog


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Upload storage path
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'instance', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── CORS — allow any frontend origin (safe because we use JWT, not cookies) ─
    CORS(app, resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])

    db.init_app(app)
    bcrypt.init_app(app)

    # ── Guarantee CORS headers on EVERY response (including errors) ──────────
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    # ── Error handlers — return JSON with CORS headers on crashes ────────────
    @app.errorhandler(500)
    def handle_500(e):
        print(f"🔴 500 ERROR: {e}")
        traceback.print_exc()
        resp = jsonify({"error": "Internal server error", "detail": str(e)})
        resp.status_code = 500
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    @app.errorhandler(404)
    def handle_404(e):
        resp = jsonify({"error": "Not found"})
        resp.status_code = 404
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    @app.errorhandler(405)
    def handle_405(e):
        resp = jsonify({"error": "Method not allowed"})
        resp.status_code = 405
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    # ── Blueprints ──────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(super_admin_bp, url_prefix="/api/super-admin")

    # ── Health check ────────────────────────────────────────────────────────────
    @app.route("/")
    @app.route("/health")
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "message": "Smart e-Print API is running 🚀"})

    # ── Debug: test DB connection ────────────────────────────────────────────────
    @app.route("/api/debug/db")
    def debug_db():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected ✅"})
        except Exception as e:
            return jsonify({"status": "error", "database": str(e)}), 500

    # ── Create tables and apply schema migrations on startup ──────────────────
    with app.app_context():
        is_sqlite = app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite')

        if is_sqlite:
            # SQLite: let SQLAlchemy create all tables from models — no raw DDL needed
            db.create_all()
            print("✅  SQLite database tables created (local dev mode)")
        else:
            # PostgreSQL: apply idempotent DDL migrations
            try:
                db.session.execute(db.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check"))
                db.session.execute(db.text(
                    "ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('customer', 'admin', 'super_admin', 'owner'))"
                ))
                db.session.execute(db.text("UPDATE users SET role = 'admin' WHERE role = 'owner'"))

                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS login_count INTEGER NOT NULL DEFAULT 0"))
                db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()"))
                db.session.execute(db.text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))

                db.session.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        user_email VARCHAR(255),
                        actor_role VARCHAR(30),
                        action VARCHAR(100) NOT NULL,
                        details TEXT,
                        ip_address VARCHAR(50),
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                db.session.execute(db.text("ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS customer_name VARCHAR(100)"))
                db.session.execute(db.text("ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS rejection_reason TEXT"))
                db.session.execute(db.text("ALTER TABLE print_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()"))
                db.session.execute(db.text("ALTER TABLE print_orders ALTER COLUMN user_id DROP NOT NULL"))

                db.session.commit()
                print("✅  PostgreSQL schema & migrations ready")
            except Exception as e:
                db.session.rollback()
                print(f"ℹ️   Migration note: {e}")

        # ── Seed Initial Accounts if not present ──────────────────────────────
        try:
            # 1. Super Admin Account
            super_admin = User.query.filter_by(role="super_admin").first()
            if not super_admin:
                sa_email = "officialsrujal@gmail.com"
                sa_user = User.query.filter_by(email=sa_email).first()
                if not sa_user:
                    sa_user = User(
                        name="Srujal Patel (Super Admin)",
                        email=sa_email,
                        password_hash=bcrypt.generate_password_hash("020807").decode("utf-8"),
                        role="super_admin",
                        is_active=True,
                    )
                    db.session.add(sa_user)
                    db.session.commit()
                    print(f"👑  Default Super Admin seeded: {sa_email} (Password: 020807)")
                else:
                    sa_user.role = "super_admin"
                    sa_user.password_hash = bcrypt.generate_password_hash("020807").decode("utf-8")
                    db.session.commit()

            # 2. Admin Account (ensure single admin exists)
            admin = User.query.filter_by(role="admin").first()
            if not admin:
                adm_email = "srujalp72@gmail.com"
                adm_user = User.query.filter_by(email=adm_email).first()
                if not adm_user:
                    adm_user = User(
                        name="Srujal Patel (Admin)",
                        email=adm_email,
                        password_hash=bcrypt.generate_password_hash("020807").decode("utf-8"),
                        role="admin",
                        is_active=True,
                    )
                    db.session.add(adm_user)
                    db.session.commit()
                    print(f"🏪  Default Admin seeded: {adm_email} (Password: 020807)")
                else:
                    adm_user.role = "admin"
                    adm_user.password_hash = bcrypt.generate_password_hash("020807").decode("utf-8")
                    db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Seeding warning: {e}")

    return app


# ── Module-level app instance (required by gunicorn: `gunicorn app:app`) ─────
app = create_app()

if __name__ == "__main__":
    print("🚀  Smart e-Print backend  →  http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
