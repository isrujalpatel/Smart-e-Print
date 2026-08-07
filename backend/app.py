from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, bcrypt
from routes.auth import auth_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ─────────────────────────────────────────────────────────────
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    db.init_app(app)
    bcrypt.init_app(app)

    # ── Blueprints ──────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # ── Health check ────────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "message": "Smart e-Print API is running 🚀"})

    # ── Create tables on first run ───────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        print("✅  Database tables ready")

    return app


if __name__ == "__main__":
    app = create_app()
    print("🚀  Smart e-Print backend  →  http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
