from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import traceback
from config import Config
from extensions import db, bcrypt
from routes.auth import auth_bp
from routes.orders import orders_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Upload storage path
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'instance', 'uploads')

    # ── CORS — allow any frontend origin (safe because we use JWT, not cookies) ─
    CORS(app, resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    db.init_app(app)
    bcrypt.init_app(app)

    # ── Guarantee CORS headers on EVERY response (including errors) ──────────
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
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

    # ── Create tables on first run ───────────────────────────────────────────────
    with app.app_context():
        try:
            db.create_all()
            print("✅  Database tables ready")
        except Exception as e:
            print(f"⚠️  Database connection failed on startup: {e}")
            print("   Tables will be created when the database becomes available.")

        # ── Schema migration: add google_id + relax password_hash (idempotent) ──
        try:
            db.session.execute(db.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)"
            ))
            db.session.execute(db.text(
                "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"
            ))
            db.session.commit()
            print("✅  Schema migration complete (google_id column ready)")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️   Migration skipped (may already be applied): {e}")

    return app


# ── Module-level app instance (required by gunicorn: `gunicorn app:app`) ─────
app = create_app()

if __name__ == "__main__":
    print("🚀  Smart e-Print backend  →  http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
