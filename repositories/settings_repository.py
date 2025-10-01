from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Settings
import logging

logger = logging.getLogger(__name__)

class SettingsRepository:
    """Repository for Settings CRUD operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self) -> Settings:
        """Get or create singleton settings with proper race condition handling"""
        # First, try to get existing settings
        settings = self.db.query(Settings).first()
        if settings:
            return settings

        # No settings exist, try to create them
        try:
            settings = Settings(singleton=True)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
            logger.debug("Created new Settings")
            return settings
        except IntegrityError:
            # Another transaction created it concurrently
            self.db.rollback()
            settings = self.db.query(Settings).first()
            if not settings:
                # This should never happen, but handle it gracefully
                raise RuntimeError("Failed to get or create Settings")
            logger.debug("Settings was created by concurrent transaction")
            return settings

    def update(self, settings: Settings, llm_model: str, max_tokens: int) -> Settings:
        """Update settings"""
        self.db.refresh(settings)
        settings.llm_model = llm_model
        settings.max_tokens = max_tokens
        self.db.commit()
        self.db.refresh(settings)
        logger.info(f"Updated Settings: model={llm_model}, tokens={max_tokens}")
        return settings
