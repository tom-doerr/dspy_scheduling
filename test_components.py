"""Unit tests for repositories and core components."""

import pytest
from datetime import datetime, timedelta
from models import Task, GlobalContext, DSPyExecution, ChatMessage, SessionLocal
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from repositories.dspy_execution_repository import DSPyExecutionRepository
from repositories.chat_repository import ChatRepository
from services.task_service import _safe_fromisoformat


@pytest.fixture
def db():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    # Clean up
    session.query(Task).delete()
    session.query(GlobalContext).delete()
    session.query(DSPyExecution).delete()
    session.query(ChatMessage).delete()
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

    def test_get_completed_tasks(self, db):
        """Test getting completed tasks only."""
        repo = TaskRepository(db)
        now = datetime.now()

        # Completed task with actual times
        completed_task = repo.create(Task(
            title="Completed",
            actual_start_time=now - timedelta(hours=2),
            actual_end_time=now - timedelta(hours=1),
            completed=True
        ))

        # Incomplete task
        incomplete_task = repo.create(Task(title="Incomplete", completed=False))

        completed = repo.get_completed()
        assert len(completed) == 1
        assert completed[0].id == completed_task.id
        assert completed[0].completed is True

    def test_get_completed_ordering(self, db):
        """Test completed tasks are ordered by actual_end_time desc (most recent first)."""
        repo = TaskRepository(db)
        now = datetime.now()

        # Create tasks with different completion times
        old_task = repo.create(Task(
            title="Old",
            actual_start_time=now - timedelta(days=3),
            actual_end_time=now - timedelta(days=3),
            completed=True
        ))
        recent_task = repo.create(Task(
            title="Recent",
            actual_start_time=now - timedelta(hours=2),
            actual_end_time=now - timedelta(hours=1),
            completed=True
        ))
        middle_task = repo.create(Task(
            title="Middle",
            actual_start_time=now - timedelta(days=1),
            actual_end_time=now - timedelta(days=1),
            completed=True
        ))

        completed = repo.get_completed()
        assert len(completed) == 3
        # Should be ordered most recent first
        assert completed[0].id == recent_task.id
        assert completed[1].id == middle_task.id
        assert completed[2].id == old_task.id


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


def test_schedule_checker_reprioritize_tasks(db):
    """Test ScheduleChecker.reprioritize_tasks updates task priorities"""
    from schedule_checker import ScheduleChecker
    from scheduler import TimeSlotModule, PrioritizedTask
    from repositories.task_repository import TaskRepository
    from repositories.context_repository import GlobalContextRepository
    from models import Task, GlobalContext
    from unittest.mock import MagicMock

    # Create test tasks
    task1 = Task(title="Task 1", priority=0.0, completed=False)
    task2 = Task(title="Task 2", priority=0.0, completed=False)
    db.add_all([task1, task2])
    db.commit()

    # Create schedule checker
    time_scheduler = TimeSlotModule()
    checker = ScheduleChecker(time_scheduler)

    # Mock the prioritizer result
    mock_result = MagicMock()
    mock_result.prioritized_tasks = [
        PrioritizedTask(id=task1.id, title="Task 1", priority=7.5, reasoning="High importance"),
        PrioritizedTask(id=task2.id, title="Task 2", priority=4.2, reasoning="Medium importance")
    ]
    checker._call_dspy_prioritizer = MagicMock(return_value=mock_result)

    # Run reprioritization
    task_repo = TaskRepository(db)
    context_repo = GlobalContextRepository(db)
    tasks_updated = checker.reprioritize_tasks(task_repo, context_repo)

    # Verify
    assert tasks_updated == 2
    db.refresh(task1)
    db.refresh(task2)
    assert task1.priority == 7.5
    assert task2.priority == 4.2


class TestChatRepository:
    """Test chat repository operations."""

    def test_create_chat_message(self, db):
        """Test creating a chat message."""
        repo = ChatRepository(db)
        msg = ChatMessage(
            user_message="Hello",
            assistant_response="Hi there!"
        )
        created = repo.create(msg)

        assert created.id is not None
        assert created.user_message == "Hello"
        assert created.assistant_response == "Hi there!"
        assert created.created_at is not None

    def test_get_recent_messages(self, db):
        """Test getting recent messages ordered by created_at desc."""
        repo = ChatRepository(db)

        # Create messages
        msg1 = repo.create(ChatMessage(user_message="First", assistant_response="Response 1"))
        msg2 = repo.create(ChatMessage(user_message="Second", assistant_response="Response 2"))
        msg3 = repo.create(ChatMessage(user_message="Third", assistant_response="Response 3"))

        recent = repo.get_recent(limit=2)
        assert len(recent) == 2
        # Should be ordered newest first
        assert recent[0].id == msg3.id
        assert recent[1].id == msg2.id

    def test_delete_all_messages(self, db):
        """Test deleting all chat messages."""
        repo = ChatRepository(db)

        # Create messages
        repo.create(ChatMessage(user_message="Msg 1", assistant_response="Resp 1"))
        repo.create(ChatMessage(user_message="Msg 2", assistant_response="Resp 2"))

        count = repo.delete_all()
        assert count == 2

        # Verify all deleted
        messages = repo.get_all()
        assert len(messages) == 0
