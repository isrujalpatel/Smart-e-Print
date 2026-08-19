from extensions import db
from datetime import datetime, timezone
import uuid


class User(db.Model):
    """User model — stores Customer, Admin, and Super Admin accounts."""

    __tablename__ = "users"

    id            = db.Column(db.String(36), primary_key=True,
                              default=lambda: str(uuid.uuid4()))
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)   # nullable for Google-only users
    role          = db.Column(db.String(20), nullable=False)   # 'customer' | 'admin' | 'super_admin'
    is_active     = db.Column(db.Boolean, nullable=False, default=True)
    last_login    = db.Column(db.DateTime, nullable=True)
    login_count   = db.Column(db.Integer, nullable=False, default=0)
    google_id     = db.Column(db.String(255), nullable=True, index=True)
    created_at    = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.email!r} role={self.role!r} active={self.is_active}>"

    @property
    def is_customer(self):
        return self.role == "customer"

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_super_admin(self):
        return self.role == "super_admin"

    def to_dict(self):
        """Safe serialization — never exposes password_hash."""
        return {
            "id":          self.id,
            "name":        self.name,
            "email":       self.email,
            "role":        self.role,
            "is_active":   self.is_active,
            "last_login":  self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
            "google_id":   self.google_id,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }
