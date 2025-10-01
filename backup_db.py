#!/usr/bin/env python3
"""Backup database to JSON file"""
import json
from datetime import datetime
from models import SessionLocal, Task, GlobalContext, DSPyExecution

def backup_database(output_file='db_backup.json'):
    """Export all data to JSON"""
    db = SessionLocal()
    try:
        backup_data = {
            'backup_time': datetime.now().isoformat(),
            'tasks': [],
            'global_context': None
        }

        # Backup tasks
        tasks = db.query(Task).all()
        for task in tasks:
            backup_data['tasks'].append({
                'title': task.title,
                'description': task.description,
                'context': task.context,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'scheduled_start_time': task.scheduled_start_time.isoformat() if task.scheduled_start_time else None,
                'scheduled_end_time': task.scheduled_end_time.isoformat() if task.scheduled_end_time else None,
                'actual_start_time': task.actual_start_time.isoformat() if task.actual_start_time else None,
                'actual_end_time': task.actual_end_time.isoformat() if task.actual_end_time else None,
                'priority': task.priority,
                'completed': task.completed,
                'needs_scheduling': task.needs_scheduling
            })

        # Backup global context
        ctx = db.query(GlobalContext).first()
        if ctx:
            backup_data['global_context'] = {'context': ctx.context}

        with open(output_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        print(f"✓ Backed up {len(backup_data['tasks'])} tasks")
        return True
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return False
    finally:
        db.close()

if __name__ == '__main__':
    backup_database()
