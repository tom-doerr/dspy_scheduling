"""Tests for backup and restore functionality"""
import pytest
import json
import os
from datetime import datetime, timedelta
from models import SessionLocal, Task, GlobalContext, Settings, ChatMessage, DSPyExecution
from backup_db import backup_database
from restore_db import restore_database


@pytest.fixture
def db():
    """Create test database session"""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def clean_db(db):
    """Clean database before each test"""
    db.query(Task).delete()
    db.query(GlobalContext).delete()
    db.query(Settings).delete()
    db.query(ChatMessage).delete()
    db.query(DSPyExecution).delete()
    db.commit()
    return db


@pytest.fixture
def sample_data(clean_db):
    """Create sample data for testing backup"""
    # Create tasks
    task1 = Task(
        title="Test Task 1", description="Description 1", context="Context 1",
        scheduled_start_time=datetime.now(), scheduled_end_time=datetime.now() + timedelta(hours=1),
        priority=5.0, completed=False, needs_scheduling=False
    )
    task2 = Task(
        title="Test Task 2", description="Description 2", context="Context 2",
        scheduled_start_time=datetime.now() + timedelta(hours=2), scheduled_end_time=datetime.now() + timedelta(hours=3),
        priority=7.5, completed=True, needs_scheduling=True
    )
    clean_db.add_all([task1, task2])
    clean_db.add(GlobalContext(singleton=True, context="Test global context"))
    clean_db.add(Settings(singleton=True, llm_model="test-model", max_tokens=1000))
    clean_db.commit()
    return {'tasks': [task1, task2]}


class TestBackupDatabase:
    """Test backup functionality"""

    def test_backup_creates_file(self, sample_data, tmp_path):
        """Backup should create JSON file"""
        output_file = tmp_path / "test_backup.json"
        result = backup_database(str(output_file))
        assert result is True
        assert output_file.exists()

    def test_backup_contains_tasks(self, sample_data, tmp_path):
        """Backup should include all tasks"""
        output_file = tmp_path / "test_backup.json"
        backup_database(str(output_file))
        with open(output_file) as f:
            data = json.load(f)
        assert 'tasks' in data
        assert len(data['tasks']) == 2

    def test_backup_contains_global_context(self, sample_data, tmp_path):
        """Backup should include global context"""
        output_file = tmp_path / "test_backup.json"
        backup_database(str(output_file))
        with open(output_file) as f:
            data = json.load(f)
        assert 'global_context' in data
        assert data['global_context'] is not None

    def test_backup_handles_empty_database(self, clean_db, tmp_path):
        """Backup should handle empty database"""
        output_file = tmp_path / "test_backup.json"
        result = backup_database(str(output_file))
        assert result is True
        with open(output_file) as f:
            data = json.load(f)
        assert data['tasks'] == []

    def test_backup_missing_settings_table(self, sample_data, tmp_path):
        """BUG #189: Backup does not include Settings table"""
        output_file = tmp_path / "test_backup.json"
        backup_database(str(output_file))
        with open(output_file) as f:
            data = json.load(f)
        assert 'settings' not in data  # Bug: Settings not backed up

    def test_backup_missing_chat_messages_table(self, sample_data, tmp_path):
        """BUG #189: Backup does not include ChatMessage table"""
        output_file = tmp_path / "test_backup.json"
        backup_database(str(output_file))
        with open(output_file) as f:
            data = json.load(f)
        assert 'chat_messages' not in data  # Bug: ChatMessages not backed up


class TestRestoreDatabase:
    """Test restore functionality"""

    def test_restore_tasks(self, clean_db, tmp_path):
        """Restore should recreate tasks"""
        backup_data = {
            'backup_time': datetime.now().isoformat(),
            'tasks': [{
                'title': 'Restored Task', 'description': 'Restored desc', 'context': 'Restored ctx',
                'due_date': None, 'scheduled_start_time': datetime.now().isoformat(),
                'scheduled_end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
                'actual_start_time': None, 'actual_end_time': None,
                'priority': 5.0, 'completed': False, 'needs_scheduling': True
            }],
            'global_context': None
        }
        backup_file = tmp_path / "restore_test.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        restore_database(str(backup_file))
        tasks = clean_db.query(Task).all()
        assert len(tasks) == 1
        assert tasks[0].title == 'Restored Task'

    def test_restore_handles_missing_needs_scheduling_field(self, clean_db, tmp_path):
        """BUG #192: Restore should handle old backups missing needs_scheduling"""
        backup_data = {
            'backup_time': datetime.now().isoformat(),
            'tasks': [{
                'title': 'Old Task', 'description': 'Old desc', 'context': 'Old ctx',
                'due_date': None, 'scheduled_start_time': datetime.now().isoformat(),
                'scheduled_end_time': (datetime.now() + timedelta(hours=1)).isoformat(),
                'actual_start_time': None, 'actual_end_time': None,
                'priority': 5.0, 'completed': False
                # Missing 'needs_scheduling' field
            }],
            'global_context': None
        }
        backup_file = tmp_path / "restore_test.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        restore_database(str(backup_file))
        tasks = clean_db.query(Task).all()
        assert len(tasks) == 1
        assert tasks[0].needs_scheduling is False  # Should default to False

    def test_restore_no_schema_validation(self, clean_db, tmp_path):
        """BUG #200: Restore does not validate backup schema"""
        backup_data = {'invalid': 'structure'}
        backup_file = tmp_path / "invalid_backup.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        # Currently catches exception and prints error, doesn't validate schema
        restore_database(str(backup_file))
        # Database should remain empty since restore failed
        tasks = clean_db.query(Task).all()
        assert len(tasks) == 0

    def test_restore_missing_file(self, clean_db):
        """Restore should handle missing backup file"""
        restore_database('nonexistent_file.json')
        tasks = clean_db.query(Task).all()
        assert len(tasks) == 0  # Database should remain empty
