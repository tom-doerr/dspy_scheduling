"""Unit tests for repositories and core components."""

import pytest
from datetime import datetime, timedelta
from models import Task, GlobalContext, SessionLocal
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository


@pytest.fixture
def db():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    # Clean up
    session.query(Task).delete()
    session.query(GlobalContext).delete()
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
