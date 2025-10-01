from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import GlobalContext
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GlobalContextRepository:
    """Repository for GlobalContext database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Optional[GlobalContext]:
        """Get the global context"""
        return self.db.query(GlobalContext).first()

    def get_or_create(self) -> GlobalContext:
        """Get or create global context with row locking to prevent race conditions"""
        # Use FOR UPDATE to lock the row and prevent concurrent creates
        context = self.db.query(GlobalContext).with_for_update().first()
        if not context:
            # Check again without lock in case another transaction just created it
            self.db.commit()  # Release any locks
            context = self.db.query(GlobalContext).first()
            if not context:
                context = GlobalContext(singleton=True, context="")
                self.db.add(context)
                self.db.commit()
                logger.debug("Created new GlobalContext")
        return context

    def update(self, context_text: str) -> GlobalContext:
        """Update global context"""
        context = self.get()
        if not context:
            context = GlobalContext(singleton=True, context=context_text)
            self.db.add(context)
        else:
            # Refresh to prevent race conditions
            self.db.refresh(context)
            context.context = context_text
            context.updated_at = datetime.now()
        self.db.commit()
        return context
