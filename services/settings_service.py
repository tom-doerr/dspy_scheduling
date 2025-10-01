from repositories.settings_repository import SettingsRepository
from models import Settings
import logging

logger = logging.getLogger(__name__)

class SettingsService:
    """Service layer for settings operations"""

    def __init__(self, settings_repo: SettingsRepository):
        self.settings_repo = settings_repo

    def get_settings(self) -> Settings:
        """Get current settings"""
        return self.settings_repo.get_or_create()

    def update_settings(self, llm_model: str, max_tokens: int) -> Settings:
        """Update application settings"""
        settings = self.settings_repo.get_or_create()
        return self.settings_repo.update(settings, llm_model, max_tokens)
