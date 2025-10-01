from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from models import Task
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for Task database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Task]:
        """Get all tasks ordered by priority and due date"""
        return self.db.query(Task).order_by(Task.priority.desc(), Task.due_date).all()

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def get_incomplete(self) -> List[Task]:
        """Get all incomplete tasks"""
        return self.db.query(Task).filter(Task.completed.is_(False)).all()

    def get_scheduled(self) -> List[Task]:
        """Get all tasks with scheduled times"""
        return self.db.query(Task).filter(Task.scheduled_start_time.isnot(None)).order_by(Task.scheduled_start_time).all()

    def get_tasks_needing_scheduling(self) -> List[Task]:
        """Get all tasks that need DSPy scheduling"""
        return self.db.query(Task).filter(Task.needs_scheduling.is_(True), Task.completed.is_(False)).all()

    def get_active(self) -> Optional[Task]:
        """Get currently active task"""
        return self.db.query(Task).filter(Task.actual_start_time.isnot(None), Task.completed.is_(False)).first()

    def get_completed(self) -> List[Task]:
        """Get all completed tasks ordered by actual end time (most recent first)"""
        return self.db.query(Task).filter(Task.completed.is_(True)).order_by(Task.actual_end_time.desc()).all()

    def create(self, task: Task) -> Task:
        """Create a new task"""
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Created task ID={task.id}: '{task.title}'")
        return task

    def delete(self, task: Task) -> None:
        """Delete a task"""
        task_id, task_title = task.id, task.title
        self.db.delete(task)
        self.db.commit()
        logger.info(f"Deleted task ID={task_id}: '{task_title}'")

    def start_task(self, task: Task) -> Task:
        """Mark task as started"""
        try:
            self.db.refresh(task)
        except InvalidRequestError:
            raise ValueError(f"Cannot start task: Task was deleted by another process")

        # Validate task state
        if task.completed:
            raise ValueError(f"Cannot start task: Task '{task.title}' is already completed")

        if not task.actual_start_time:
            # Check if another task is already active
            active_task = self.get_active()
            if active_task and active_task.id != task.id:
                raise ValueError(f"Cannot start task: Another task '{active_task.title}' is already active")

            task.actual_start_time = datetime.now()

            try:
                self.db.commit()
                logger.info(f"Started task ID={task.id}: '{task.title}'")
            except IntegrityError:
                self.db.rollback()
                # Re-check for active task after rollback
                active_task = self.get_active()
                if active_task:
                    raise ValueError(f"Cannot start task: Another task '{active_task.title}' is already active")
                else:
                    raise ValueError(f"Cannot start task: Database constraint violation")
        return task

    def stop_task(self, task: Task) -> Task:
        """Stop a task by clearing actual_start_time"""
        try:
            self.db.refresh(task)
        except InvalidRequestError:
            raise ValueError(f"Cannot stop task: Task was deleted by another process")

        # Validate task state
        if task.completed:
            raise ValueError(f"Cannot stop task: Task '{task.title}' is already completed")

        if not task.actual_start_time:
            raise ValueError(f"Cannot stop task: Task '{task.title}' is not started")

        task.actual_start_time = None
        self.db.commit()
        logger.info(f"Stopped task ID={task.id}: '{task.title}'")
        return task

    def complete_task(self, task: Task) -> Task:
        """Mark task as completed"""
        try:
            self.db.refresh(task)
        except InvalidRequestError:
            raise ValueError(f"Cannot complete task: Task was deleted by another process")

        # Validate task state
        if not task.actual_start_time:
            raise ValueError(f"Cannot complete task: Task '{task.title}' has not been started")

        task.completed = True
        task.actual_end_time = datetime.now()
        self.db.commit()
        logger.info(f"Completed task ID={task.id}: '{task.title}'")
        return task
