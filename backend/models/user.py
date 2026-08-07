from extensions import db
from datetime import datetime, timezone
import uuid


class User(db.Model):
    """User model — stores both Customer and Owner accounts."""

    __tablename__ = "users"

    id           = db.Column(db.String(36), primary_key=True,
                             default=lambda: str(uuid.uuid4()))
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role         = db.Column(db.String(20), nullable=False)   # 'customer' | 'owner'
    created_at   = db.Column(db.DateTime,
                             default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.email!r} role={self.role!r}>"

    def to_dict(self):
        """Safe serialization — never exposes password_hash."""
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "role":       self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
