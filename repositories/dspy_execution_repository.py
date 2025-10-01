from sqlalchemy.orm import Session
from models import DSPyExecution
from typing import List
import logging

logger = logging.getLogger(__name__)


class DSPyExecutionRepository:
    """Repository for DSPyExecution database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, limit: int = 50) -> List[DSPyExecution]:
        """Get latest executions ordered by creation time (newest first)"""
        return self.db.query(DSPyExecution).order_by(DSPyExecution.created_at.desc()).limit(limit).all()

    def create(self, execution: DSPyExecution) -> DSPyExecution:
        """Create a new execution record"""
        self.db.add(execution)
        self.db.commit()
        logger.debug(f"Logged DSPy execution: {execution.module_name} ({execution.duration_ms:.2f}ms)")
        return execution
