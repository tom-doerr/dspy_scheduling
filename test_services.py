"""Unit tests for service layer with error handling and edge cases"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from models import Base, Task, ChatMessage
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from repositories.chat_repository import ChatRepository
from services.task_service import TaskService, _safe_fromisoformat
from services.chat_service import ChatService
from config import settings


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def task_repo(test_db):
    return TaskRepository(test_db)


@pytest.fixture
def context_repo(test_db):
    return GlobalContextRepository(test_db)


@pytest.fixture
def chat_repo(test_db):
    return ChatRepository(test_db)


class TestTaskServiceErrorHandling:
    """Test error handling in TaskService"""

    def test_create_task_with_invalid_due_date(self, task_repo, context_repo):
        """Test task creation with invalid due_date format"""
        mock_scheduler = Mock()
        service = TaskService(task_repo, context_repo, mock_scheduler)

        task = service.create_task(
            title="Test Task",
            description="Description",
            context="Context",
            due_date="invalid-date-format"
        )

        assert task.title == "Test Task"
        assert task.due_date is None

    def test_schedule_task_dspy_failure(self, task_repo, context_repo):
        """Test DSPy scheduler failure with fallback"""
        mock_scheduler = Mock(side_effect=Exception("DSPy API Error"))
        service = TaskService(task_repo, context_repo, mock_scheduler)

        task = service.create_task("Test", "Desc", "Context", None)
        original_start = task.scheduled_start_time
        original_end = task.scheduled_end_time

        result = service.schedule_task_with_dspy(task)

        assert result.scheduled_start_time == original_start
        assert result.scheduled_end_time == original_end
        assert result.needs_scheduling is False

    def test_schedule_task_dspy_retry_logic(self, task_repo, context_repo):
        """Test DSPy retry logic on temporary failures"""
        mock_scheduler = Mock(side_effect=[
            Exception("Temporary error 1"),
            Exception("Temporary error 2"),
            MagicMock(
                start_time=datetime.now().isoformat(),
                end_time=(datetime.now() + timedelta(hours=2)).isoformat()
            )
        ])
        service = TaskService(task_repo, context_repo, mock_scheduler)

        task = service.create_task("Test", "Desc", "Context", None)
        result = service.schedule_task_with_dspy(task)

        assert result.needs_scheduling is False
        assert mock_scheduler.call_count == 3

    def test_start_task_not_found(self, task_repo, context_repo):
        """Test starting non-existent task"""
        mock_scheduler = Mock()
        service = TaskService(task_repo, context_repo, mock_scheduler)
        result = service.start_task(99999)
        assert result is None

    def test_delete_task_success(self, task_repo, context_repo):
        """Test successful task deletion"""
        mock_scheduler = Mock()
        service = TaskService(task_repo, context_repo, mock_scheduler)
        task = service.create_task("Test", "Desc", "Context", None)
        task_id = task.id
        result = service.delete_task(task_id)
        assert result is True
        assert service.task_repo.get_by_id(task_id) is None

    def test_delete_task_not_found(self, task_repo, context_repo):
        """Test deleting non-existent task"""
        mock_scheduler = Mock()
        service = TaskService(task_repo, context_repo, mock_scheduler)
        result = service.delete_task(99999)
        assert result is False


class TestChatServiceErrorHandling:
    """Test error handling in ChatService"""

    def test_execute_action_create_task_minimal_fields(self, chat_repo, task_repo, context_repo):
        """Test creating task with minimal fields via chat"""
        service = ChatService(chat_repo, task_repo, context_repo)
        result = service._execute_action(
            action="create_task",
            task_id=None,
            title="",
            description="",
            context=""
        )
        assert result["success"] is True
        assert "Untitled Task" in result["message"]

    def test_execute_action_start_task_not_found(self, chat_repo, task_repo, context_repo):
        """Test starting non-existent task via chat"""
        service = ChatService(chat_repo, task_repo, context_repo)
        result = service._execute_action(
            action="start_task",
            task_id=99999,
            title="",
            description="",
            context=""
        )
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_execute_action_delete_task_not_found(self, chat_repo, task_repo, context_repo):
        """Test deleting non-existent task via chat"""
        service = ChatService(chat_repo, task_repo, context_repo)
        result = service._execute_action(
            action="delete_task",
            task_id=99999,
            title="",
            description="",
            context=""
        )
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_get_task_list_json_empty(self, chat_repo, task_repo, context_repo):
        """Test getting task list when no tasks exist"""
        service = ChatService(chat_repo, task_repo, context_repo)
        task_list = service._get_task_list_json()
        assert task_list == "[]"


class TestSafeFromISOFormat:
    """Test _safe_fromisoformat helper function"""

    def test_valid_datetime(self):
        """Test parsing valid ISO datetime"""
        dt_str = "2025-01-15T10:30:00"
        result = _safe_fromisoformat(dt_str)
        assert result is not None
        assert result.year == 2025

    def test_none_input(self):
        """Test None input"""
        result = _safe_fromisoformat(None)
        assert result is None

    def test_empty_string(self):
        """Test empty string"""
        result = _safe_fromisoformat("")
        assert result is None

    def test_invalid_format(self):
        """Test invalid format"""
        result = _safe_fromisoformat("not-a-date")
        assert result is None


class TestChatServiceIntegration:
    """Integration tests for ChatService with mocked DSPy"""

    @patch('services.chat_service.ChatAssistantModule')
    def test_process_message_with_create_action(self, mock_assistant_class, chat_repo, task_repo, context_repo):
        """Test processing message that creates a task"""
        mock_result = MagicMock()
        mock_result.action = "create_task"
        mock_result.task_id = None
        mock_result.title = "New Task"
        mock_result.description = "Description"
        mock_result.context = "Context"
        mock_result.response = "I've created a task"

        mock_assistant = MagicMock()
        mock_assistant.forward.return_value = mock_result
        mock_assistant_class.return_value = mock_assistant

        service = ChatService(chat_repo, task_repo, context_repo)
        result = service.process_message("Create a task")

        assert "created a task" in result.assistant_response.lower()
        tasks = task_repo.get_all()
        assert len(tasks) == 1

    @patch('services.chat_service.ChatAssistantModule')
    def test_process_message_action_failure(self, mock_assistant_class, chat_repo, task_repo, context_repo):
        """Test processing message when action fails"""
        mock_result = MagicMock()
        mock_result.action = "start_task"
        mock_result.task_id = 99999
        mock_result.response = "Starting the task"

        mock_assistant = MagicMock()
        mock_assistant.forward.return_value = mock_result
        mock_assistant_class.return_value = mock_assistant

        service = ChatService(chat_repo, task_repo, context_repo)
        result = service.process_message("Start task 99999")

        assert "not found" in result.assistant_response.lower()
