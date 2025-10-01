from sqlalchemy.orm import Session
from models import Settings
import logging

logger = logging.getLogger(__name__)

class SettingsRepository:
    """Repository for Settings CRUD operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self) -> Settings:
        """Get or create singleton settings"""
        settings = self.db.query(Settings).with_for_update().first()
        if not settings:
            settings = Settings(singleton=True)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, settings: Settings, llm_model: str, max_tokens: int) -> Settings:
        """Update settings"""
        self.db.refresh(settings)
        settings.llm_model = llm_model
        settings.max_tokens = max_tokens
        self.db.commit()
        self.db.refresh(settings)
        return settings
