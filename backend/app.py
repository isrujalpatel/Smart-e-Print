from flask import Flask, jsonify
from flask_cors import CORS
import os
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
    CORS(app)

    # Guarantee CORS headers on every response (including errors)
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    db.init_app(app)
    bcrypt.init_app(app)

    # ── Blueprints ──────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")

    # ── Health check ────────────────────────────────────────────────────────────
    @app.route("/")
    @app.route("/health")
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "message": "Smart e-Print API is running 🚀"})

    # ── Create tables on first run ───────────────────────────────────────────────
    with app.app_context():
        try:
            db.create_all()
            print("✅  Database tables ready")
        except Exception as e:
            print(f"⚠️  Database connection failed on startup: {e}")
            print("   Tables will be created when the database becomes available.")

    return app

# ── Module-level app instance (required by gunicorn: `gunicorn app:app`) ─────
app = create_app()

if __name__ == "__main__":
    print("🚀  Smart e-Print backend  →  http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
