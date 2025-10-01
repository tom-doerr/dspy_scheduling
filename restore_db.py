#!/usr/bin/env python3
import json
from datetime import datetime
from models import SessionLocal, Task, GlobalContext

def restore_database(input_file='db_backup.json'):
    db = SessionLocal()
    try:
        with open(input_file, 'r') as f:
            backup_data = json.load(f)

        print(f"Restoring from {backup_data['backup_time']}")

        # Restore global context
        if backup_data.get('global_context'):
            ctx = db.query(GlobalContext).first()
            if not ctx:
                ctx = GlobalContext(singleton=True)
                db.add(ctx)
            ctx.context = backup_data['global_context']['context']

        # Restore tasks
        for t in backup_data['tasks']:
            task = Task(
                title=t['title'], description=t['description'], context=t['context'],
                due_date=datetime.fromisoformat(t['due_date']) if t['due_date'] else None,
                scheduled_start_time=datetime.fromisoformat(t['scheduled_start_time']) if t['scheduled_start_time'] else None,
                scheduled_end_time=datetime.fromisoformat(t['scheduled_end_time']) if t['scheduled_end_time'] else None,
                actual_start_time=datetime.fromisoformat(t['actual_start_time']) if t['actual_start_time'] else None,
                actual_end_time=datetime.fromisoformat(t['actual_end_time']) if t['actual_end_time'] else None,
                priority=t['priority'], completed=t['completed'],
                needs_scheduling=t.get('needs_scheduling', False)
            )
            db.add(task)

        db.commit()
        print(f"✓ Restored {len(backup_data['tasks'])} tasks")
    except Exception as e:
        print(f"✗ Failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    restore_database()
