"""Unit tests for repositories and core components."""

import pytest
from datetime import datetime, timedelta
from models import Task, GlobalContext, DSPyExecution, SessionLocal
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from repositories.dspy_execution_repository import DSPyExecutionRepository
from services.task_service import _safe_fromisoformat


@pytest.fixture
def db():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    # Clean up
    session.query(Task).delete()
    session.query(GlobalContext).delete()
    session.query(DSPyExecution).delete()
    session.commit()
    yield session
    session.close()


class TestTaskRepository:
    """Test task repository CRUD operations."""

    def test_create_task(self, db):
        """Test creating a task through repository."""
        repo = TaskRepository(db)
        task = Task(
            title="Test Task",
            description="Test Description",
            context="Test Context"
        )
        created = repo.create(task)

        assert created.id is not None
        assert created.title == "Test Task"
        assert created.description == "Test Description"
        assert created.context == "Test Context"
        assert created.completed is False

    def test_get_all_tasks(self, db):
        """Test getting all tasks."""
        repo = TaskRepository(db)
        repo.create(Task(title="Task 1", description="", context=""))
        repo.create(Task(title="Task 2", description="", context=""))

        tasks = repo.get_all()
        assert len(tasks) == 2

    def test_get_incomplete_tasks(self, db):
        """Test getting incomplete tasks."""
        repo = TaskRepository(db)
        task1 = repo.create(Task(title="Incomplete", description="", context=""))
        task2 = repo.create(Task(title="Complete", description="", context=""))

        task2.completed = True
        db.commit()

        incomplete = repo.get_incomplete()
        assert len(incomplete) == 1
        assert incomplete[0].id == task1.id


class TestGlobalContextRepository:
    """Test global context repository operations."""

    def test_get_or_create_context(self, db):
        """Test get or create global context."""
        repo = GlobalContextRepository(db)

        # First call should create
        context1 = repo.get_or_create()
        assert context1.id is not None
        assert context1.context == ""

        # Second call should return same
        context2 = repo.get_or_create()
        assert context2.id == context1.id


class TestDSPyExecutionRepository:
    """Test DSPy execution repository operations."""

    def test_create_execution(self, db):
        """Test creating a DSPy execution log."""
        repo = DSPyExecutionRepository(db)
        execution = DSPyExecution(
            module_name="TimeSlotModule",
            inputs='{"task": "test"}',
            outputs='{"start": "2025-10-01T09:00"}',
            duration_ms=1500.0
        )
        created = repo.create(execution)

        assert created.id is not None
        assert created.module_name == "TimeSlotModule"
        assert created.duration_ms == 1500.0

    def test_get_latest_executions(self, db):
        """Test getting latest executions ordered by creation time."""
        repo = DSPyExecutionRepository(db)

        # Create multiple executions
        for i in range(5):
            repo.create(DSPyExecution(
                module_name=f"Module{i}",
                inputs=f'{{"input": {i}}}',
                outputs=f'{{"output": {i}}}',
                duration_ms=float(i * 100)
            ))

        latest = repo.get_latest(limit=3)
        assert len(latest) == 3
        # Should be ordered newest first
        assert latest[0].module_name == "Module4"
        assert latest[1].module_name == "Module3"
        assert latest[2].module_name == "Module2"


class TestTaskServiceHelpers:
    """Test TaskService helper functions."""

    def test_safe_fromisoformat_valid_datetime(self):
        """Test parsing valid ISO format datetime."""
        result = _safe_fromisoformat("2025-10-01T09:00:00", "test_field")
        assert result is not None
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 1
        assert result.hour == 9

    def test_safe_fromisoformat_none(self):
        """Test parsing None returns None."""
        result = _safe_fromisoformat(None, "test_field")
        assert result is None

    def test_safe_fromisoformat_empty_string(self):
        """Test parsing empty string returns None."""
        result = _safe_fromisoformat("", "test_field")
        assert result is None

    def test_safe_fromisoformat_invalid_format(self):
        """Test parsing invalid format returns None and logs error."""
        result = _safe_fromisoformat("not-a-date", "test_field")
        assert result is None

    def test_safe_fromisoformat_partial_datetime(self):
        """Test parsing datetime without time component."""
        result = _safe_fromisoformat("2025-10-01", "test_field")
        assert result is not None
        assert result.year == 2025
