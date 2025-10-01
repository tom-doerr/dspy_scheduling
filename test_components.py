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
    from models import Settings
    session = SessionLocal()
    # Clean up
    session.query(Task).delete()
    session.query(GlobalContext).delete()
    session.query(DSPyExecution).delete()
    session.query(ChatMessage).delete()
    session.query(Settings).delete()
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

    def test_get_by_id(self, db):
        """Test getting task by ID."""
        repo = TaskRepository(db)
        task = repo.create(Task(title="Test Task"))

        found = repo.get_by_id(task.id)
        assert found is not None
        assert found.id == task.id
        assert found.title == "Test Task"

        # Test non-existent ID
        not_found = repo.get_by_id(99999)
        assert not_found is None

    def test_get_scheduled(self, db):
        """Test getting tasks with scheduled times."""
        repo = TaskRepository(db)
        now = datetime.now()

        # Task with scheduled times
        scheduled_task = repo.create(Task(
            title="Scheduled",
            scheduled_start_time=now + timedelta(hours=1),
            scheduled_end_time=now + timedelta(hours=2)
        ))

        # Task without scheduled times
        unscheduled_task = repo.create(Task(title="Unscheduled"))

        scheduled = repo.get_scheduled()
        assert len(scheduled) == 1
        assert scheduled[0].id == scheduled_task.id

    def test_get_tasks_needing_scheduling(self, db):
        """Test getting tasks that need DSPy scheduling."""
        repo = TaskRepository(db)

        # Task needing scheduling
        needs_scheduling = repo.create(Task(
            title="Needs Scheduling",
            needs_scheduling=True,
            completed=False
        ))

        # Task already scheduled
        already_scheduled = repo.create(Task(
            title="Already Scheduled",
            needs_scheduling=False,
            completed=False
        ))

        # Completed task needing scheduling (should not be returned)
        completed_task = repo.create(Task(
            title="Completed",
            needs_scheduling=True,
            completed=True
        ))

        tasks = repo.get_tasks_needing_scheduling()
        assert len(tasks) == 1
        assert tasks[0].id == needs_scheduling.id

    def test_get_active(self, db):
        """Test getting active task."""
        repo = TaskRepository(db)
        now = datetime.now()

        # Started task
        started_task = repo.create(Task(
            title="Started",
            actual_start_time=now,
            completed=False
        ))

        # Not started task
        not_started = repo.create(Task(title="Not Started", completed=False))

        active = repo.get_active()
        assert active is not None
        assert active.id == started_task.id


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


def test_schedule_checker_reschedule_task(db):
    """Test ScheduleChecker.reschedule_task updates task times"""
    from schedule_checker import ScheduleChecker, ScheduledTask
    from scheduler import TimeSlotModule
    from repositories.task_repository import TaskRepository
    from repositories.context_repository import GlobalContextRepository
    from models import Task
    from unittest.mock import MagicMock

    # Create test task
    now = datetime.now()
    task = Task(
        title="Test Task",
        needs_scheduling=True,
        completed=False,
        scheduled_start_time=now + timedelta(hours=1),
        scheduled_end_time=now + timedelta(hours=2)
    )
    db.add(task)
    db.commit()

    # Create schedule checker
    time_scheduler = TimeSlotModule()
    checker = ScheduleChecker(time_scheduler)

    # Mock the DSPy call
    mock_result = MagicMock()
    new_start = (now + timedelta(hours=3)).isoformat()
    new_end = (now + timedelta(hours=4)).isoformat()
    mock_result.start_time = new_start
    mock_result.end_time = new_end
    checker._call_dspy_reschedule = MagicMock(return_value=mock_result)

    # Run reschedule
    task_repo = TaskRepository(db)
    context_repo = GlobalContextRepository(db)
    checker.reschedule_task(task_repo, context_repo, task, now)

    # Verify task was updated
    db.refresh(task)
    assert task.scheduled_start_time.isoformat() == new_start
    assert task.scheduled_end_time.isoformat() == new_end


def test_schedule_checker_reschedule_invalid_datetime(db):
    """Test ScheduleChecker handles invalid datetime formats gracefully"""
    from schedule_checker import ScheduleChecker
    from scheduler import TimeSlotModule
    from repositories.task_repository import TaskRepository
    from repositories.context_repository import GlobalContextRepository
    from models import Task
    from unittest.mock import MagicMock

    # Create test task
    now = datetime.now()
    task = Task(title="Test Task", needs_scheduling=True, completed=False)
    db.add(task)
    db.commit()

    # Create schedule checker
    time_scheduler = TimeSlotModule()
    checker = ScheduleChecker(time_scheduler)

    # Mock DSPy call with invalid datetime strings
    mock_result = MagicMock()
    mock_result.start_time = "invalid-datetime"
    mock_result.end_time = "also-invalid"
    checker._call_dspy_reschedule = MagicMock(return_value=mock_result)

    # Run reschedule
    task_repo = TaskRepository(db)
    context_repo = GlobalContextRepository(db)
    checker.reschedule_task(task_repo, context_repo, task, now)

    # Verify task times are None (fallback behavior)
    db.refresh(task)
    assert task.scheduled_start_time is None
    assert task.scheduled_end_time is None


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


class TestSettingsRepository:
    """Test settings repository operations."""

    def test_get_or_create_settings(self, db):
        """Test get or create settings."""
        from repositories.settings_repository import SettingsRepository

        repo = SettingsRepository(db)

        # First call should create
        settings1 = repo.get_or_create()
        assert settings1.id is not None
        assert settings1.llm_model == "openrouter/deepseek/deepseek-v3.2-exp"
        assert settings1.max_tokens == 2000

        # Second call should return same
        settings2 = repo.get_or_create()
        assert settings2.id == settings1.id

    def test_update_settings(self, db):
        """Test updating settings."""
        from repositories.settings_repository import SettingsRepository

        repo = SettingsRepository(db)
        settings = repo.get_or_create()

        # Update settings
        updated = repo.update(settings, "gpt-4", 4000)
        assert updated.llm_model == "gpt-4"
        assert updated.max_tokens == 4000


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


class TestAuditRecordArchival:
    """Test audit record archival functionality."""

    def test_delete_old_dspy_executions(self, db):
        """Test deleting old DSPy execution records."""
        repo = DSPyExecutionRepository(db)

        # Create old and recent records
        old_date = datetime.now() - timedelta(days=35)
        recent_date = datetime.now() - timedelta(days=5)

        # Old records (should be deleted)
        old1 = DSPyExecution(
            module_name="TimeSlotModule",
            inputs="old input 1",
            outputs="old output 1",
            duration_ms=100.0,
            created_at=old_date
        )
        old2 = DSPyExecution(
            module_name="PrioritizerModule",
            inputs="old input 2",
            outputs="old output 2",
            duration_ms=150.0,
            created_at=old_date
        )

        # Recent records (should be kept)
        recent1 = DSPyExecution(
            module_name="TimeSlotModule",
            inputs="recent input",
            outputs="recent output",
            duration_ms=120.0,
            created_at=recent_date
        )

        repo.create(old1)
        repo.create(old2)
        repo.create(recent1)

        # Delete records older than 30 days
        deleted_count = repo.delete_old_records(retention_days=30)
        assert deleted_count == 2

        # Verify only recent records remain
        remaining = repo.get_latest(limit=10)
        assert len(remaining) == 1
        assert remaining[0].inputs == "recent input"

    def test_delete_old_chat_messages(self, db):
        """Test deleting old chat messages."""
        repo = ChatRepository(db)

        # Create old and recent messages
        old_date = datetime.now() - timedelta(days=40)
        recent_date = datetime.now() - timedelta(days=10)

        # Old messages (should be deleted)
        old1 = ChatMessage(
            user_message="Old user msg 1",
            assistant_response="Old assistant resp 1",
            created_at=old_date
        )
        old2 = ChatMessage(
            user_message="Old user msg 2",
            assistant_response="Old assistant resp 2",
            created_at=old_date
        )

        # Recent messages (should be kept)
        recent1 = ChatMessage(
            user_message="Recent user msg",
            assistant_response="Recent assistant resp",
            created_at=recent_date
        )

        repo.create(old1)
        repo.create(old2)
        repo.create(recent1)

        # Delete messages older than 30 days
        deleted_count = repo.delete_old_records(retention_days=30)
        assert deleted_count == 2

        # Verify only recent messages remain
        remaining = repo.get_all()
        assert len(remaining) == 1
        assert remaining[0].user_message == "Recent user msg"

    def test_delete_old_records_none_to_delete(self, db):
        """Test delete_old_records when no old records exist."""
        dspy_repo = DSPyExecutionRepository(db)
        chat_repo = ChatRepository(db)

        # Create only recent records
        recent_date = datetime.now() - timedelta(days=5)

        dspy_repo.create(DSPyExecution(
            module_name="TimeSlotModule",
            inputs="input",
            outputs="output",
            duration_ms=100.0,
            created_at=recent_date
        ))

        chat_repo.create(ChatMessage(
            user_message="User msg",
            assistant_response="Assistant resp",
            created_at=recent_date
        ))

        # Delete old records (should delete nothing)
        dspy_deleted = dspy_repo.delete_old_records(retention_days=30)
        chat_deleted = chat_repo.delete_old_records(retention_days=30)

        assert dspy_deleted == 0
        assert chat_deleted == 0

        # Verify records still exist
        assert len(dspy_repo.get_latest(10)) == 1
        assert len(chat_repo.get_all()) == 1
