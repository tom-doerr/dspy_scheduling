from repositories.dspy_execution_repository import DSPyExecutionRepository
from models import DSPyExecution
from typing import List


class InferenceService:
    """Service layer for DSPy inference operations"""

    def __init__(self, execution_repo: DSPyExecutionRepository):
        self.execution_repo = execution_repo

    def get_latest_executions(self, limit: int = 50) -> List[DSPyExecution]:
        """Get latest inference executions"""
        return self.execution_repo.get_latest(limit)
