from extensions import db
from datetime import datetime, timezone
import uuid

class ShopConfig(db.Model):
    """Store dynamic shop configuration like rate cards."""

    __tablename__ = "shop_configs"

    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    config_val = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "key": self.config_key,
            "val": self.config_val,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
