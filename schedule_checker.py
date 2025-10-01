from datetime import datetime
from models import SessionLocal, Task, GlobalContext
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
import logging
import dspy
from scheduler import TimeSlotModule, ScheduledTask
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os

logger = logging.getLogger(__name__)

# Global time_scheduler instance (set from app.py)
time_scheduler = None

def set_time_scheduler(scheduler):
    """Set the time scheduler instance from main app"""
    global time_scheduler
    time_scheduler = scheduler

def get_time_scheduler():
    """Get the time scheduler instance"""
    return time_scheduler

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def _call_dspy_reschedule(task_title, task_context, global_context, current_datetime, existing_schedule):
    """Call DSPy scheduler with retry logic for rescheduling"""
    logger.info(f"Calling DSPy scheduler for rescheduling '{task_title}' (with retry)")
    return time_scheduler(
        new_task=task_title,
        task_context=task_context,
        global_context=global_context,
        current_datetime=current_datetime,
        existing_schedule=existing_schedule
    )

def reschedule_task(task_repo, context_repo, task, now):
    """Reschedule a single task using DSPy"""
    if time_scheduler is None:
        logger.warning("Time scheduler not initialized, skipping reschedule")
        return

    # Get current schedule excluding this task
    all_scheduled = task_repo.get_scheduled()
    existing_tasks = [t for t in all_scheduled if t.id != task.id and not t.completed]
    existing_schedule = [ScheduledTask(id=t.id, title=t.title, start_time=str(t.scheduled_start_time),
                        end_time=str(t.scheduled_end_time)) for t in existing_tasks]

    # Reschedule with DSPy (with retry logic)
    global_context_obj = context_repo.get_or_create()
    global_context = global_context_obj.context or ""

    try:
        result = _call_dspy_reschedule(
            task_title=task.title,
            task_context=task.context or "Rescheduling overdue task",
            global_context=global_context,
            current_datetime=now.isoformat(),
            existing_schedule=existing_schedule
        )
    except Exception as e:
        logger.error(f"Failed to reschedule task '{task.title}' after retries: {e}")
        return

    # Refresh task and update with new times
    task_repo.db.refresh(task)
    task.scheduled_start_time = datetime.fromisoformat(result.start_time)
    task.scheduled_end_time = datetime.fromisoformat(result.end_time)
    task_repo.db.commit()

    logger.info(f"✅ Rescheduled '{task.title}': {result.start_time} → {result.end_time}")

def check_and_update_schedule():
    """Check if tasks need rescheduling based on current time"""
    logger.info("🔍 Schedule Check STARTED")

    db = SessionLocal()
    try:
        # Create repositories
        task_repo = TaskRepository(db)
        context_repo = GlobalContextRepository(db)

        now = datetime.now()
        tasks_rescheduled = 0

        # Get all incomplete tasks using repository
        all_tasks = task_repo.get_incomplete()

        for task in all_tasks:
            needs_reschedule = False

            if task.scheduled_end_time and task.scheduled_end_time < now and not task.completed:
                logger.info(f"⚠️  Task '{task.title}' end time passed, rescheduling...")
                needs_reschedule = True
            elif task.scheduled_start_time and task.scheduled_start_time < now and not task.actual_start_time:
                logger.info(f"⚠️  Task '{task.title}' start time passed, not started, rescheduling...")
                needs_reschedule = True

            if needs_reschedule:
                reschedule_task(task_repo, context_repo, task, now)
                tasks_rescheduled += 1

        if tasks_rescheduled > 0:
            logger.info(f"🔄 Rescheduled {tasks_rescheduled} task(s)")
        else:
            logger.info("✅ Schedule is up to date")

        logger.info("🔍 Schedule Check COMPLETED")

        return tasks_rescheduled
    finally:
        db.close()
