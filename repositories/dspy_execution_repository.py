from sqlalchemy.orm import Session
from models import DSPyExecution
from typing import List


class DSPyExecutionRepository:
    """Repository for DSPyExecution database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, limit: int = 50) -> List[DSPyExecution]:
        """Get latest executions ordered by creation time (oldest first)"""
        return self.db.query(DSPyExecution).order_by(DSPyExecution.created_at.asc()).limit(limit).all()

    def create(self, execution: DSPyExecution) -> DSPyExecution:
        """Create a new execution record"""
        self.db.add(execution)
        self.db.commit()
        return execution
