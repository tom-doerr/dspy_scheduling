from sqlalchemy.orm import Session
from models import Task
from typing import List, Optional
from datetime import datetime


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
        return self.db.query(Task).filter(Task.completed == False).all()

    def get_scheduled(self) -> List[Task]:
        """Get all tasks with scheduled times"""
        return self.db.query(Task).filter(Task.scheduled_start_time.isnot(None)).order_by(Task.scheduled_start_time).all()

    def get_active(self) -> Optional[Task]:
        """Get currently active task"""
        return self.db.query(Task).filter(Task.actual_start_time.isnot(None), Task.completed == False).first()

    def create(self, task: Task) -> Task:
        """Create a new task"""
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        """Delete a task"""
        self.db.delete(task)
        self.db.commit()

    def start_task(self, task: Task) -> Task:
        """Mark task as started"""
        self.db.refresh(task)

        # Validate task state
        if task.completed:
            raise ValueError(f"Cannot start task: Task '{task.title}' is already completed")

        if not task.actual_start_time:
            # Check if another task is already active
            active_task = self.get_active()
            if active_task and active_task.id != task.id:
                raise ValueError(f"Cannot start task: Another task '{active_task.title}' is already active")
            task.actual_start_time = datetime.now()
            self.db.commit()
        return task

    def complete_task(self, task: Task) -> Task:
        """Mark task as completed"""
        self.db.refresh(task)

        # Validate task state
        if not task.actual_start_time:
            raise ValueError(f"Cannot complete task: Task '{task.title}' has not been started")

        task.completed = True
        task.actual_end_time = datetime.now()
        self.db.commit()
        return task
