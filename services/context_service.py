from repositories.context_repository import GlobalContextRepository


class ContextService:
    """Service layer for global context operations"""

    def __init__(self, context_repo: GlobalContextRepository):
        self.context_repo = context_repo

    def get_context(self) -> str:
        """Get global context text"""
        context_obj = self.context_repo.get_or_create()
        return context_obj.context or ""

    def update_context(self, context_text: str) -> str:
        """Update global context"""
        context_obj = self.context_repo.update(context_text)
        return context_obj.context
