from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from models import Task
from datetime import datetime, timedelta
from typing import List, Optional
from scheduler import ScheduledTask
from config import settings
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


def _safe_fromisoformat(date_str: Optional[str], field_name: str = "date") -> Optional[datetime]:
    """Safely parse ISO format datetime string with error logging"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid {field_name} format: {date_str}, error: {e}")
        return None


class TaskService:
    """Service layer for task operations"""

    def __init__(self, task_repo: TaskRepository, context_repo: GlobalContextRepository, time_scheduler):
        self.task_repo = task_repo
        self.context_repo = context_repo
        self.time_scheduler = time_scheduler

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return self.task_repo.get_all()

    def get_scheduled_tasks(self) -> List[Task]:
        """Get scheduled tasks"""
        return self.task_repo.get_scheduled()

    def get_active_task(self) -> Optional[Task]:
        """Get active task"""
        return self.task_repo.get_active()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def _call_dspy_scheduler(self, new_task: str, task_context: str, global_context: str, current_datetime: str, existing_schedule: list):
        """Call DSPy scheduler with retry logic"""
        logger.info(f"Calling DSPy scheduler for task '{new_task}' (with retry)")
        return self.time_scheduler(
            new_task=new_task,
            task_context=task_context,
            global_context=global_context,
            current_datetime=current_datetime,
            existing_schedule=existing_schedule
        )

    def create_task(self, title: str, description: str, context: str, due_date: Optional[str]) -> Task:
        """Create a new task with DSPy scheduling

        Note: DSPy execution tracking uses a separate session for isolation.
        All database operations within this method use the same transaction.
        """
        try:
            current_datetime = datetime.now().isoformat()
            existing_tasks = self.task_repo.get_scheduled()
            existing_schedule = [
                ScheduledTask(id=t.id, title=t.title, start_time=str(t.scheduled_start_time), end_time=str(t.scheduled_end_time))
                for t in existing_tasks
            ]

            global_context = self.context_repo.get_or_create().context or ""

            result = self._call_dspy_scheduler(
                new_task=title,
                task_context=context,
                global_context=global_context,
                current_datetime=current_datetime,
                existing_schedule=existing_schedule
            )

            logger.info(f"📤 OUTPUT - Start: {result.start_time}, End: {result.end_time}")

            task = Task(
                title=title,
                description=description,
                context=context,
                due_date=_safe_fromisoformat(due_date, "due_date"),
                scheduled_start_time=_safe_fromisoformat(result.start_time, "start_time"),
                scheduled_end_time=_safe_fromisoformat(result.end_time, "end_time")
            )

            return self.task_repo.create(task)

        except Exception as e:
            # Repository handles rollback automatically on exception
            logger.error(f"Failed to create task '{title}': {e}")
            return self._create_fallback_task(title, description, context, due_date)

    def start_task(self, task_id: int) -> Optional[Task]:
        """Start a task"""
        task = self.task_repo.get_by_id(task_id)
        if task:
            return self.task_repo.start_task(task)
        return None

    def complete_task(self, task_id: int) -> Optional[Task]:
        """Complete a task"""
        task = self.task_repo.get_by_id(task_id)
        if task:
            return self.task_repo.complete_task(task)
        return None

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        task = self.task_repo.get_by_id(task_id)
        if task:
            self.task_repo.delete(task)
            return True
        return False

    def _create_fallback_task(self, title: str, description: str, context: str, due_date: Optional[str]) -> Task:
        """Create task with fallback scheduling when DSPy fails"""
        fallback_start = datetime.now().replace(
            hour=settings.fallback_start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        if fallback_start < datetime.now():
            fallback_start = fallback_start + timedelta(days=1)

        fallback_end = fallback_start + timedelta(hours=settings.fallback_duration_hours)

        task = Task(
            title=title,
            description=description,
            context=context,
            due_date=_safe_fromisoformat(due_date, "due_date"),
            scheduled_start_time=fallback_start,
            scheduled_end_time=fallback_end
        )

        return self.task_repo.create(task)
