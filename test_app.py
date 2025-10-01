import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app import app
from models import Base, engine, SessionLocal, Task, GlobalContext, DSPyExecution
from scheduler import ScheduledTask
import os

# Set test database
os.environ['DATABASE_URL'] = 'sqlite:///test_tasks.db'

@pytest.fixture(scope="function")
def client():
    """Create a test client and reset database"""
    # Create tables
    Base.metadata.create_all(engine)

    # Clear all data
    db = SessionLocal()
    db.query(Task).delete()
    db.query(GlobalContext).delete()
    db.query(DSPyExecution).delete()
    db.commit()
    db.close()

    yield TestClient(app)

    # Cleanup
    db = SessionLocal()
    db.query(Task).delete()
    db.query(GlobalContext).delete()
    db.query(DSPyExecution).delete()
    db.commit()
    db.close()

def test_index_page(client):
    """Test main page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"DSPy Task Scheduler" in response.content

def test_calendar_page(client):
    """Test calendar page loads"""
    response = client.get("/calendar")
    assert response.status_code == 200

def test_get_tasks_empty(client):
    """Test getting tasks when none exist"""
    response = client.get("/tasks")
    assert response.status_code == 200

def test_start_task(client):
    """Test starting a task sets actual_start_time"""
    db = SessionLocal()
    task = Task(title="Test Task", description="Test")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    response = client.post(f"/tasks/{task_id}/start")
    assert response.status_code == 200

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task.actual_start_time is not None
    db.close()

def test_complete_task(client):
    """Test completing a task"""
    db = SessionLocal()
    task = Task(title="Test Task")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    response = client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 200

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task.completed == True
    assert task.actual_end_time is not None
    db.close()

def test_delete_task(client):
    """Test deleting a task"""
    db = SessionLocal()
    task = Task(title="Test Task")
    db.add(task)
    db.commit()
    task_id = task.id
    db.close()

    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task is None
    db.close()

def test_global_context_create(client):
    """Test creating global context"""
    response = client.post("/global-context", data={"context": "I prefer mornings"})
    assert response.status_code == 200

    db = SessionLocal()
    context = db.query(GlobalContext).first()
    assert context is not None
    assert context.context == "I prefer mornings"
    db.close()

def test_get_inference_log(client):
    """Test getting inference log"""
    db = SessionLocal()
    execution = DSPyExecution(
        module_name="TestModule",
        inputs='{"test": "input"}',
        outputs='{"test": "output"}',
        duration_ms=100.5
    )
    db.add(execution)
    db.commit()
    db.close()

    response = client.get("/inference-log")
    assert response.status_code == 200
    assert b"TestModule" in response.content

def test_active_task(client):
    """Test active task shows started task"""
    db = SessionLocal()
    task = Task(
        title="Active Task",
        actual_start_time=datetime.now(),
        completed=False
    )
    db.add(task)
    db.commit()
    db.close()

    response = client.get("/active-task")
    assert response.status_code == 200
    assert b"Active Task" in response.content

def test_timezone_consistency_task_creation(client):
    """Test that task created_at uses local time not UTC"""
    db = SessionLocal()
    before = datetime.now()
    task = Task(title="Timezone Test")
    db.add(task)
    db.commit()
    db.refresh(task)
    after = datetime.now()

    assert task.created_at >= before
    assert task.created_at <= after
    assert task.created_at.tzinfo is None
    db.close()

def test_timezone_consistency_global_context(client):
    """Test that global context updated_at uses local time"""
    db = SessionLocal()
    before = datetime.now()
    context = GlobalContext(context="Test")
    db.add(context)
    db.commit()
    db.refresh(context)
    after = datetime.now()

    assert context.updated_at >= before
    assert context.updated_at <= after
    assert context.updated_at.tzinfo is None
    db.close()

def test_timezone_consistency_dspy_execution(client):
    """Test that DSPy execution created_at uses local time"""
    db = SessionLocal()
    before = datetime.now()
    execution = DSPyExecution(
        module_name="Test",
        inputs="{}",
        outputs="{}",
        duration_ms=100.0
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    after = datetime.now()

    assert execution.created_at >= before
    assert execution.created_at <= after
    assert execution.created_at.tzinfo is None
    db.close()

def test_task_id_autoincrement(client):
    """Test that task IDs auto-increment correctly"""
    db = SessionLocal()

    task1 = Task(title="Task 1")
    task2 = Task(title="Task 2")
    task3 = Task(title="Task 3")

    db.add(task1)
    db.commit()
    db.refresh(task1)

    db.add(task2)
    db.commit()
    db.refresh(task2)

    db.add(task3)
    db.commit()
    db.refresh(task3)

    assert task1.id is not None
    assert task2.id is not None
    assert task3.id is not None
    assert task2.id > task1.id
    assert task3.id > task2.id

    db.close()

def test_global_context_id_autoincrement(client):
    """Test that GlobalContext IDs auto-increment correctly"""
    db = SessionLocal()

    context1 = GlobalContext(context="Context 1")
    context2 = GlobalContext(context="Context 2")

    db.add(context1)
    db.commit()
    db.refresh(context1)

    db.add(context2)
    db.commit()
    db.refresh(context2)

    assert context1.id is not None
    assert context2.id is not None
    assert context2.id > context1.id

    db.close()

def test_dspy_execution_id_autoincrement(client):
    """Test that DSPyExecution IDs auto-increment correctly"""
    db = SessionLocal()

    exec1 = DSPyExecution(module_name="Module1", inputs="{}", outputs="{}", duration_ms=10.0)
    exec2 = DSPyExecution(module_name="Module2", inputs="{}", outputs="{}", duration_ms=20.0)

    db.add(exec1)
    db.commit()
    db.refresh(exec1)

    db.add(exec2)
    db.commit()
    db.refresh(exec2)

    assert exec1.id is not None
    assert exec2.id is not None
    assert exec2.id > exec1.id

    db.close()

def test_scheduled_task_has_id_field():
    """Test that ScheduledTask model includes id field"""
    task = ScheduledTask(
        id=123,
        title="Test Task",
        start_time="2025-10-01T10:00:00",
        end_time="2025-10-01T11:00:00"
    )

    assert task.id == 123
    assert task.title == "Test Task"
    assert task.start_time == "2025-10-01T10:00:00"
    assert task.end_time == "2025-10-01T11:00:00"

def test_scheduled_task_serialization():
    """Test that ScheduledTask serializes with id field"""
    task = ScheduledTask(
        id=456,
        title="Serialization Test",
        start_time="2025-10-01T14:00:00",
        end_time="2025-10-01T15:00:00"
    )

    task_dict = task.dict()

    assert "id" in task_dict
    assert task_dict["id"] == 456
    assert task_dict["title"] == "Serialization Test"
    assert task_dict["start_time"] == "2025-10-01T14:00:00"
    assert task_dict["end_time"] == "2025-10-01T15:00:00"

def test_task_to_scheduled_task_includes_id(client):
    """Test that converting Task to ScheduledTask includes the id"""
    db = SessionLocal()

    task = Task(
        title="Task with ID",
        scheduled_start_time=datetime(2025, 10, 1, 10, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 11, 0, 0)
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    scheduled_task = ScheduledTask(
        id=task.id,
        title=task.title,
        start_time=str(task.scheduled_start_time),
        end_time=str(task.scheduled_end_time)
    )

    assert scheduled_task.id == task.id
    assert scheduled_task.title == task.title

    db.close()

def test_existing_schedule_excludes_current_task(client):
    """Test that when building existing_schedule, current task is excluded"""
    db = SessionLocal()

    task1 = Task(
        title="Task 1",
        scheduled_start_time=datetime(2025, 10, 1, 10, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 11, 0, 0)
    )
    task2 = Task(
        title="Task 2 (to reschedule)",
        scheduled_start_time=datetime(2025, 10, 1, 12, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 13, 0, 0)
    )
    task3 = Task(
        title="Task 3",
        scheduled_start_time=datetime(2025, 10, 1, 14, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 15, 0, 0)
    )

    db.add_all([task1, task2, task3])
    db.commit()
    db.refresh(task1)
    db.refresh(task2)
    db.refresh(task3)

    # Simulate building existing_schedule excluding task2
    existing_tasks = db.query(Task).filter(
        Task.scheduled_start_time.isnot(None),
        Task.completed == False,
        Task.id != task2.id
    ).all()

    existing_schedule = [
        ScheduledTask(
            id=t.id,
            title=t.title,
            start_time=str(t.scheduled_start_time),
            end_time=str(t.scheduled_end_time)
        ) for t in existing_tasks
    ]

    assert len(existing_schedule) == 2
    assert all(s.id != task2.id for s in existing_schedule)
    assert any(s.id == task1.id for s in existing_schedule)
    assert any(s.id == task3.id for s in existing_schedule)

    db.close()

def test_id_uniqueness_across_models(client):
    """Test that IDs are unique and independent across different models"""
    db = SessionLocal()

    task = Task(title="Task")
    context = GlobalContext(context="Context")
    execution = DSPyExecution(module_name="Module", inputs="{}", outputs="{}", duration_ms=10.0)

    db.add_all([task, context, execution])
    db.commit()
    db.refresh(task)
    db.refresh(context)
    db.refresh(execution)

    assert task.id is not None
    assert context.id is not None
    assert execution.id is not None

    db.close()

def test_end_to_end_id_flow(client):
    """Test that task IDs flow correctly from DB to ScheduledTask to dict"""
    db = SessionLocal()

    # Create tasks in database
    task1 = Task(
        title="Morning Task",
        scheduled_start_time=datetime(2025, 10, 1, 9, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 10, 0, 0)
    )
    task2 = Task(
        title="Afternoon Task",
        scheduled_start_time=datetime(2025, 10, 1, 14, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 15, 0, 0)
    )

    db.add_all([task1, task2])
    db.commit()
    db.refresh(task1)
    db.refresh(task2)

    db_task1_id = task1.id
    db_task2_id = task2.id

    # Query tasks back from database
    db = SessionLocal()
    tasks = db.query(Task).filter(Task.scheduled_start_time.isnot(None)).all()

    # Convert to ScheduledTask objects (mimicking app.py behavior)
    existing_schedule = [
        ScheduledTask(
            id=t.id,
            title=t.title,
            start_time=str(t.scheduled_start_time),
            end_time=str(t.scheduled_end_time)
        ) for t in tasks
    ]

    # Verify IDs are preserved in ScheduledTask objects
    assert len(existing_schedule) == 2
    assert any(s.id == db_task1_id for s in existing_schedule)
    assert any(s.id == db_task2_id for s in existing_schedule)

    # Verify IDs are preserved in dict serialization (for DSPy logging)
    schedule_dicts = [s.dict() for s in existing_schedule]
    assert all("id" in d for d in schedule_dicts)
    assert any(d["id"] == db_task1_id for d in schedule_dicts)
    assert any(d["id"] == db_task2_id for d in schedule_dicts)

    db.close()

def test_tasks_displayed_in_html(client):
    """Test that tasks are properly displayed in the HTML response"""
    db = SessionLocal()

    task1 = Task(
        title="Morning Meeting",
        description="Team standup",
        scheduled_start_time=datetime(2025, 10, 1, 9, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 10, 0, 0)
    )
    task2 = Task(
        title="Afternoon Work",
        description="Code review",
        scheduled_start_time=datetime(2025, 10, 1, 14, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 16, 0, 0)
    )

    db.add_all([task1, task2])
    db.commit()
    db.close()

    response = client.get("/tasks")
    assert response.status_code == 200
    assert b"Morning Meeting" in response.content
    assert b"Afternoon Work" in response.content
    assert b"Team standup" in response.content
    assert b"Code review" in response.content

def test_task_item_html_structure(client):
    """Test that individual task HTML contains expected elements"""
    db = SessionLocal()

    task = Task(
        title="Test Task Structure",
        description="Description text",
        priority=7.5,
        scheduled_start_time=datetime(2025, 10, 1, 10, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 11, 0, 0)
    )

    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    response = client.get("/tasks")
    html = response.content.decode('utf-8')

    assert f'id="task-{task_id}"' in html
    assert "Test Task Structure" in html
    assert "Priority:" in html
    assert "7.5" in html
    assert "Scheduled:" in html
    assert "2025-10-01 10:00" in html
    assert "2025-10-01 11:00" in html

def test_completed_task_styling(client):
    """Test that completed tasks have the completed class"""
    db = SessionLocal()

    task = Task(
        title="Completed Task",
        completed=True,
        actual_end_time=datetime.now()
    )

    db.add(task)
    db.commit()
    db.close()

    response = client.get("/tasks")
    html = response.content.decode('utf-8')

    assert 'class="task' in html
    assert 'completed' in html
    assert "Completed Task" in html
