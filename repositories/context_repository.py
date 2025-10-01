from sqlalchemy.orm import Session
from models import GlobalContext
from typing import Optional


class GlobalContextRepository:
    """Repository for GlobalContext database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Optional[GlobalContext]:
        """Get the global context"""
        return self.db.query(GlobalContext).first()

    def get_or_create(self) -> GlobalContext:
        """Get or create global context"""
        context = self.get()
        if not context:
            context = GlobalContext(context="")
            self.db.add(context)
            self.db.commit()
        return context

    def update(self, context_text: str) -> GlobalContext:
        """Update global context"""
        context = self.get()
        if not context:
            context = GlobalContext(context=context_text)
            self.db.add(context)
        else:
            context.context = context_text
        self.db.commit()
        return context
