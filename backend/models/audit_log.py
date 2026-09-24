from extensions import db
from datetime import datetime, timezone
import uuid


class AuditLog(db.Model):
    """Audit log model — tracks user and administrative actions."""

    __tablename__ = "audit_logs"

    id         = db.Column(db.String(36), primary_key=True,
                          default=lambda: str(uuid.uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = db.Column(db.String(255), nullable=True)
    actor_role = db.Column(db.String(30), nullable=True)
    action     = db.Column(db.String(100), nullable=False)
    details    = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="audit_logs", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "user_email": self.user_email,
            "actor_role": self.actor_role,
            "action":     self.action,
            "details":    self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def log(cls, action, user=None, user_email=None, actor_role=None, details=None, ip_address=None):
        """Helper to create and commit an audit log entry."""
        if user:
            u_id = user.id
            u_email = user.email
            a_role = user.role
        else:
            u_id = None
            u_email = user_email
            a_role = actor_role

        log_entry = cls(
            user_id=u_id,
            user_email=u_email,
            actor_role=a_role,
            action=action,
            details=details,
            ip_address=ip_address,
        )
        try:
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[WARN] AuditLog write failed (non-fatal): {e}")
        return log_entry
