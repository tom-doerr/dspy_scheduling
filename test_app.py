import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app import app
from models import Base, Task, GlobalContext, DSPyExecution, SessionLocal
from scheduler import ScheduledTask
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Global test engine and session maker
test_engine = None
TestSessionLocal = None

@pytest.fixture(scope="function")
def client():
    """Create a test client with isolated database"""
    global test_engine, TestSessionLocal

    # Create unique temporary database for this test
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Set test database URL
    test_db_url = f'sqlite:///{temp_db_path}'
    os.environ['DATABASE_URL'] = test_db_url

    # Create engine and session for this test
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    # Create tables
    Base.metadata.create_all(test_engine)

    # Override get_db dependency to use test database
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from models import get_db
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    # Clear overrides
    app.dependency_overrides.clear()

    # Cleanup: close engine and delete temp database
    test_engine.dispose()
    try:
        os.unlink(temp_db_path)
    except Exception:
        pass  # Best effort cleanup

@pytest.fixture(scope="function")
def db_session(client):
    """Provide database session for tests that need direct DB access"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
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

def test_start_task(client, db_session):
    """Test starting a task sets actual_start_time"""
    task = Task(title="Test Task", description="Test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    task_id = task.id

    response = client.post(f"/tasks/{task_id}/start")
    assert response.status_code == 200

    db_session.expire_all()
    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task.actual_start_time is not None

def test_complete_task(client, db_session):
    """Test completing a task"""
    task = Task(title="Test Task", actual_start_time=datetime.now())
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    task_id = task.id

    response = client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 200

    db_session.expire_all()
    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task.completed == True
    assert task.actual_end_time is not None

def test_delete_task(client, db_session):
    """Test deleting a task"""
    task = Task(title="Test Task")
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200

    db_session.expire_all()
    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task is None

def test_global_context_create(client, db_session):
    """Test creating global context"""
    response = client.post("/global-context", data={"context": "I prefer mornings"})
    assert response.status_code == 200

    db_session.expire_all()
    context = db_session.query(GlobalContext).first()
    assert context is not None
    assert context.context == "I prefer mornings"

def test_get_inference_log(client, db_session):
    """Test getting inference log"""
    execution = DSPyExecution(
        module_name="TestModule",
        inputs='{"test": "input"}',
        outputs='{"test": "output"}',
        duration_ms=100.5
    )
    db_session.add(execution)
    db_session.commit()

    response = client.get("/inference-log")
    assert response.status_code == 200
    assert b"TestModule" in response.content

def test_active_task(client, db_session):
    """Test active task shows started task"""
    task = Task(
        title="Active Task",
        actual_start_time=datetime.now(),
        completed=False
    )
    db_session.add(task)
    db_session.commit()

    response = client.get("/active-task")
    assert response.status_code == 200
    assert b"Active Task" in response.content

def test_timezone_consistency_task_creation(client, db_session):
    """Test that task created_at uses local time not UTC"""
    before = datetime.now()
    task = Task(title="Timezone Test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    after = datetime.now()

    assert task.created_at >= before
    assert task.created_at <= after
    assert task.created_at.tzinfo is None

def test_timezone_consistency_global_context(client, db_session):
    """Test that global context updated_at uses local time"""
    before = datetime.now()
    context = GlobalContext(context="Test")
    db_session.add(context)
    db_session.commit()
    db_session.refresh(context)
    after = datetime.now()

    assert context.updated_at >= before
    assert context.updated_at <= after
    assert context.updated_at.tzinfo is None

def test_timezone_consistency_dspy_execution(client, db_session):
    """Test that DSPy execution created_at uses local time"""
    before = datetime.now()
    execution = DSPyExecution(
        module_name="Test",
        inputs="{}",
        outputs="{}",
        duration_ms=100.0
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)
    after = datetime.now()

    assert execution.created_at >= before
    assert execution.created_at <= after
    assert execution.created_at.tzinfo is None

def test_task_id_autoincrement(client, db_session):
    """Test that task IDs auto-increment correctly"""
    task1 = Task(title="Task 1")
    task2 = Task(title="Task 2")
    task3 = Task(title="Task 3")

    db_session.add(task1)
    db_session.commit()
    db_session.refresh(task1)

    db_session.add(task2)
    db_session.commit()
    db_session.refresh(task2)

    db_session.add(task3)
    db_session.commit()
    db_session.refresh(task3)

    assert task1.id is not None
    assert task2.id is not None
    assert task3.id is not None
    assert task2.id > task1.id
    assert task3.id > task2.id

def test_global_context_singleton_constraint(client, db_session):
    """Test that only one GlobalContext can exist (singleton constraint)"""
    context1 = GlobalContext(context="Context 1", singleton=True)
    db_session.add(context1)
    db_session.commit()
    db_session.refresh(context1)

    # Attempting to create a second GlobalContext should fail
    from sqlalchemy.exc import IntegrityError
    context2 = GlobalContext(context="Context 2", singleton=True)
    db_session.add(context2)

    with pytest.raises(IntegrityError):
        db_session.commit()

def test_dspy_execution_id_autoincrement(client, db_session):
    """Test that DSPyExecution IDs auto-increment correctly"""
    exec1 = DSPyExecution(module_name="Module1", inputs="{}", outputs="{}", duration_ms=10.0)
    exec2 = DSPyExecution(module_name="Module2", inputs="{}", outputs="{}", duration_ms=20.0)

    db_session.add(exec1)
    db_session.commit()
    db_session.refresh(exec1)

    db_session.add(exec2)
    db_session.commit()
    db_session.refresh(exec2)

    assert exec1.id is not None
    assert exec2.id is not None
    assert exec2.id > exec1.id

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

    task_dict = task.model_dump()

    assert "id" in task_dict
    assert task_dict["id"] == 456
    assert task_dict["title"] == "Serialization Test"
    assert task_dict["start_time"] == "2025-10-01T14:00:00"
    assert task_dict["end_time"] == "2025-10-01T15:00:00"

def test_task_to_scheduled_task_includes_id(client, db_session):
    """Test that converting Task to ScheduledTask includes the id"""
    task = Task(
        title="Task with ID",
        scheduled_start_time=datetime(2025, 10, 1, 10, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 11, 0, 0)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    scheduled_task = ScheduledTask(
        id=task.id,
        title=task.title,
        start_time=str(task.scheduled_start_time),
        end_time=str(task.scheduled_end_time)
    )

    assert scheduled_task.id == task.id
    assert scheduled_task.title == task.title

def test_existing_schedule_excludes_current_task(client, db_session):
    """Test that when building existing_schedule, current task is excluded"""
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

    db_session.add_all([task1, task2, task3])
    db_session.commit()
    db_session.refresh(task1)
    db_session.refresh(task2)
    db_session.refresh(task3)

    # Simulate building existing_schedule excluding task2
    existing_tasks = db_session.query(Task).filter(
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

def test_id_uniqueness_across_models(client, db_session):
    """Test that IDs are unique and independent across different models"""
    task = Task(title="Task")
    context = GlobalContext(context="Context")
    execution = DSPyExecution(module_name="Module", inputs="{}", outputs="{}", duration_ms=10.0)

    db_session.add_all([task, context, execution])
    db_session.commit()
    db_session.refresh(task)
    db_session.refresh(context)
    db_session.refresh(execution)

    assert task.id is not None
    assert context.id is not None
    assert execution.id is not None

def test_end_to_end_id_flow(client, db_session):
    """Test that task IDs flow correctly from DB to ScheduledTask to dict"""
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

    db_session.add_all([task1, task2])
    db_session.commit()
    db_session.refresh(task1)
    db_session.refresh(task2)

    db_task1_id = task1.id
    db_task2_id = task2.id

    # Query tasks back from database
    tasks = db_session.query(Task).filter(Task.scheduled_start_time.isnot(None)).all()

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
    schedule_dicts = [s.model_dump() for s in existing_schedule]
    assert all("id" in d for d in schedule_dicts)
    assert any(d["id"] == db_task1_id for d in schedule_dicts)
    assert any(d["id"] == db_task2_id for d in schedule_dicts)

def test_tasks_displayed_in_html(client, db_session):
    """Test that tasks are properly displayed in the HTML response"""
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

    db_session.add_all([task1, task2])
    db_session.commit()

    response = client.get("/tasks")
    assert response.status_code == 200
    assert b"Morning Meeting" in response.content
    assert b"Afternoon Work" in response.content
    assert b"Team standup" in response.content
    assert b"Code review" in response.content

def test_task_item_html_structure(client, db_session):
    """Test that individual task HTML contains expected elements"""
    task = Task(
        title="Test Task Structure",
        description="Description text",
        priority=7.5,
        scheduled_start_time=datetime(2025, 10, 1, 10, 0, 0),
        scheduled_end_time=datetime(2025, 10, 1, 11, 0, 0)
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    task_id = task.id

    response = client.get("/tasks")
    html = response.content.decode('utf-8')

    assert f'id="task-{task_id}"' in html
    assert "Test Task Structure" in html
    assert "Priority:" in html
    assert "7.5" in html
    assert "Scheduled:" in html
    assert "2025-10-01 10:00" in html
    assert "2025-10-01 11:00" in html

def test_completed_task_styling(client, db_session):
    """Test that completed tasks have the completed class"""
    task = Task(
        title="Completed Task",
        completed=True,
        actual_end_time=datetime.now()
    )

    db_session.add(task)
    db_session.commit()

    response = client.get("/tasks")
    html = response.content.decode('utf-8')

    assert 'class="task' in html
    assert 'completed' in html
    assert "Completed Task" in html

# Validation and error handling tests

def test_create_task_with_title_too_long(client):
    """Test that creating a task with title > 200 chars fails"""
    response = client.post("/tasks", data={
        "title": "x" * 201,
        "description": "Valid description"
    })
    assert response.status_code == 422

def test_create_task_with_description_too_long(client):
    """Test that creating a task with description > 1000 chars fails"""
    response = client.post("/tasks", data={
        "title": "Valid title",
        "description": "x" * 1001
    })
    assert response.status_code == 422

def test_start_completed_task(client, db_session):
    """Test that starting a completed task returns 400"""
    task = Task(title="Completed", completed=True, actual_start_time=datetime.now(), actual_end_time=datetime.now())
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.post(f"/tasks/{task.id}/start")
    assert response.status_code == 400

def test_complete_not_started_task(client, db_session):
    """Test that completing a task that hasn't been started returns 400"""
    task = Task(title="Not Started")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.post(f"/tasks/{task.id}/complete")
    assert response.status_code == 400
    assert b"not been started" in response.content.lower()

def test_start_nonexistent_task(client):
    """Test that starting a nonexistent task returns 404"""
    response = client.post("/tasks/99999/start")
    assert response.status_code == 404

def test_invalid_task_id_rejected(client):
    """Test that invalid task IDs (<=0) are rejected"""
    response = client.post("/tasks/0/start")
    assert response.status_code == 422

    response = client.post("/tasks/-1/start")
    assert response.status_code == 422

def test_global_context_too_long(client):
    """Test that global context > 5000 chars fails"""
    response = client.post("/global-context", data={
        "context": "x" * 5001
    })
    assert response.status_code == 422

def test_multiple_active_tasks_prevented(client, db_session):
    """Test that starting a second task while one is active fails"""
    task1 = Task(title="Active Task 1", actual_start_time=datetime.now())
    task2 = Task(title="Task 2")
    db_session.add_all([task1, task2])
    db_session.commit()
    db_session.refresh(task2)

    response = client.post(f"/tasks/{task2.id}/start")
    assert response.status_code == 400


def test_config_validation_scheduler_interval():
    """Test that config validates scheduler_interval_seconds is positive"""
    import os
    from config import Settings
    from pydantic import ValidationError

    original = os.environ.get('SCHEDULER_INTERVAL_SECONDS')

    try:
        os.environ['SCHEDULER_INTERVAL_SECONDS'] = '-5'
        with pytest.raises(ValidationError):
            Settings()
    finally:
        if original:
            os.environ['SCHEDULER_INTERVAL_SECONDS'] = original
        elif 'SCHEDULER_INTERVAL_SECONDS' in os.environ:
            del os.environ['SCHEDULER_INTERVAL_SECONDS']


def test_config_validation_fallback_hour():
    """Test that config validates fallback_start_hour is in range 0-23"""
    import os
    from config import Settings
    from pydantic import ValidationError

    original = os.environ.get('FALLBACK_START_HOUR')

    try:
        os.environ['FALLBACK_START_HOUR'] = '25'
        with pytest.raises(ValidationError):
            Settings()
    finally:
        if original:
            os.environ['FALLBACK_START_HOUR'] = original
        elif 'FALLBACK_START_HOUR' in os.environ:
            del os.environ['FALLBACK_START_HOUR']


def test_health_endpoint_structure():
    """Test that health endpoint returns proper structure"""
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "dspy_scheduler" in data["components"]
    assert "background_scheduler" in data["components"]


# Priority Setting Tests

def test_task_priority_default_value(db_session):
    """Test that new tasks have default priority of 0.0"""
    task = Task(
        title="Test Task",
        description="Test description"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.priority == 0.0


def test_task_priority_can_be_set(db_session):
    """Test that task priority can be set to a specific value"""
    task = Task(
        title="High Priority Task",
        priority=8.5
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.priority == 8.5


def test_task_priority_update(db_session):
    """Test that task priority can be updated"""
    task = Task(title="Task", priority=5.0)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    task.priority = 9.0
    db_session.commit()
    db_session.refresh(task)

    assert task.priority == 9.0


def test_task_priority_range_values(db_session):
    """Test that task priority accepts values in 0-10 range"""
    # Test min value
    task1 = Task(title="Min Priority", priority=0.0)
    db_session.add(task1)

    # Test max value
    task2 = Task(title="Max Priority", priority=10.0)
    db_session.add(task2)

    # Test mid value
    task3 = Task(title="Mid Priority", priority=5.5)
    db_session.add(task3)

    db_session.commit()
    db_session.refresh(task1)
    db_session.refresh(task2)
    db_session.refresh(task3)

    assert task1.priority == 0.0
    assert task2.priority == 10.0
    assert task3.priority == 5.5


def test_task_priority_sorting(db_session):
    """Test that tasks can be sorted by priority"""
    task1 = Task(title="Low", priority=2.0)
    task2 = Task(title="High", priority=9.0)
    task3 = Task(title="Medium", priority=5.0)

    db_session.add_all([task1, task2, task3])
    db_session.commit()

    tasks = db_session.query(Task).order_by(Task.priority.desc()).all()

    assert len(tasks) == 3
    assert tasks[0].title == "High"
    assert tasks[0].priority == 9.0
    assert tasks[1].title == "Medium"
    assert tasks[1].priority == 5.0
    assert tasks[2].title == "Low"
    assert tasks[2].priority == 2.0


def test_task_priority_negative_value(db_session):
    """Test that negative priority values are allowed (database accepts floats)"""
    task = Task(title="Negative Priority", priority=-1.0)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.priority == -1.0


def test_task_priority_above_ten(db_session):
    """Test that priority values above 10 are allowed (database accepts floats)"""
    task = Task(title="Above Max", priority=15.0)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.priority == 15.0


def test_prioritized_task_model_validation():
    """Test PrioritizedTask Pydantic model validates priority range (0-10)"""
    from scheduler import PrioritizedTask
    from pydantic import ValidationError

    # Valid priority
    task = PrioritizedTask(
        id=1,
        title="Valid Task",
        priority=7.5,
        reasoning="High importance"
    )
    assert task.priority == 7.5
    assert task.reasoning == "High importance"

    # Test min boundary
    task_min = PrioritizedTask(id=2, title="Min", priority=0.0, reasoning="Lowest")
    assert task_min.priority == 0.0

    # Test max boundary
    task_max = PrioritizedTask(id=3, title="Max", priority=10.0, reasoning="Highest")
    assert task_max.priority == 10.0

    # Test below range (should fail)
    try:
        PrioritizedTask(id=4, title="Below", priority=-1.0, reasoning="Invalid")
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass

    # Test above range (should fail)
    try:
        PrioritizedTask(id=5, title="Above", priority=11.0, reasoning="Invalid")
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_task_input_model():
    """Test TaskInput Pydantic model for priority setting"""
    from scheduler import TaskInput

    # Basic task input
    task = TaskInput(id=1, title="Test Task", description="Test description")
    assert task.id == 1
    assert task.title == "Test Task"
    assert task.description == "Test description"
    assert task.due_date is None

    # Task with due date
    task_with_due = TaskInput(
        id=2,
        title="Urgent Task",
        description="Important",
        due_date="2025-10-15T10:00:00"
    )
    assert task_with_due.due_date == "2025-10-15T10:00:00"


def test_task_priority_filter_high(db_session):
    """Test filtering tasks by priority threshold"""
    task1 = Task(title="Low Priority", priority=2.0)
    task2 = Task(title="Medium Priority", priority=5.0)
    task3 = Task(title="High Priority", priority=8.5)
    task4 = Task(title="Critical Priority", priority=9.5)

    db_session.add_all([task1, task2, task3, task4])
    db_session.commit()

    # Get high priority tasks (>=7.0)
    high_priority_tasks = db_session.query(Task).filter(Task.priority >= 7.0).all()

    assert len(high_priority_tasks) == 2
    titles = [t.title for t in high_priority_tasks]
    assert "High Priority" in titles
    assert "Critical Priority" in titles


def test_task_priority_persists_after_other_updates(db_session):
    """Test that priority value persists when other fields are updated"""
    task = Task(title="Task", priority=7.0)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Update other fields
    task.description = "Updated description"
    task.completed = True
    db_session.commit()
    db_session.refresh(task)

    # Priority should remain unchanged
    assert task.priority == 7.0
    assert task.description == "Updated description"
    assert task.completed is True


def test_multiple_tasks_different_priorities(db_session):
    """Test that multiple tasks can have different priority values"""
    tasks = [
        Task(title=f"Task {i}", priority=float(i))
        for i in range(11)  # 0 through 10
    ]

    db_session.add_all(tasks)
    db_session.commit()

    retrieved_tasks = db_session.query(Task).order_by(Task.priority).all()

    assert len(retrieved_tasks) == 11
    for i, task in enumerate(retrieved_tasks):
        assert task.priority == float(i)
        assert task.title == f"Task {i}"
