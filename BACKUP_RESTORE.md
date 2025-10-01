# Database Backup & Restore Guide

## Your tasks are safe! The database persists between restarts.

The `tasks.db` file is stored in your project directory and persists across Docker restarts.

## Quick Commands

### Backup your tasks
```bash
docker compose exec web python backup_db.py
```
Creates `db_backup.json` with all your tasks and context.

### Restore from backup
```bash
docker compose exec web python restore_db.py
```
Restores tasks from `db_backup.json`.

## When to backup

**Before schema changes:**
```bash
# 1. Backup first
docker compose exec web python backup_db.py

# 2. Then migrate
docker compose exec web python migrate_db.py

# 3. Restore if needed
docker compose exec web python restore_db.py
```

**Before container rebuild:**
```bash
docker compose exec web python backup_db.py
docker compose down
docker compose up --build -d
```

## The database is persistent

- `tasks.db` is in your project folder (mounted as volume)
- Survives `docker compose restart`
- Survives `docker compose down && docker compose up`
- Only lost if you delete it manually or run `migrate_db.py`

## Backup files are git-ignored

`db_backup.json` and `db_backup_*.json` are in .gitignore
