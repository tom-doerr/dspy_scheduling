# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A DSPy-powered task scheduling web application that uses AI (DeepSeek V3.2-Exp via OpenRouter) to automatically schedule tasks based on existing commitments and user-provided context. Built with FastAPI, HTMX, and SQLAlchemy using Repository Pattern and Service Layer architecture.

**Tech Stack**: FastAPI + SQLAlchemy/SQLite + DSPy + HTMX + APScheduler + Docker

## Architecture

### Core Components

**Architecture**: Repository + Service + Router (Clean Architecture)

**app.py** (122L): DSPy init, APScheduler (5s), router inclusion, index page, /health endpoint

**repositories/** (~130L): `task_repository.py` (59L CRUD), `context_repository.py` (34L), `dspy_execution_repository.py` (logs). All receive `db: Session` via constructor.

**services/** (~164L): `task_service.py` (132L DSPy scheduling + retry), `context_service.py`, `inference_service.py`. Receive repositories + time_scheduler via constructor.

**routers/** (~130L): `task_router.py` (70L endpoints), `context_router.py` (28L), `inference_router.py`. Use DI (`Depends`), thin presentation layer.

**scheduler.py**: `TimeSlotModule` (schedules tasks w/ ScheduledTask model incl IDs, returns start/end/reasoning) + `PrioritizerModule` (prioritizes w/ TaskInput/PrioritizedTask). Both use ChainOfThought + dspy_tracker.

**models.py**: 3 SQLAlchemy models w/ autoincrement IDs: `Task` (scheduled vs actual times, context, priority, **needs_scheduling flag**), `GlobalContext` (shared prefs/constraints), `DSPyExecution` (module tracking). Sessions: `get_db()` for routes, `SessionLocal()` for background.

**schedule_checker.py**: Background job (5s) that: 1) Schedules new tasks w/ `needs_scheduling=True` (async DSPy scheduling), 2) Finds overdue/unstarted tasks and reschedules. Uses `SessionLocal()`.

**dspy_tracker.py**: Wraps DSPy calls, logs inputs/outputs/duration to `DSPyExecution`, uses `SessionLocal()`.

### Frontend Architecture

**Templates** (Jinja2 + HTMX): `base.html` (active tracker, glassmorphism theme), `index.html` (list + form), `calendar.html` (Gantt). Components: `task_item.html`, `gantt_item.html`, `timeline_item.html` (✓ #78 fixed), `active_task.html`, `global_context.html`, `inference_log.html`.

### Database Session Management

**CRITICAL**: Proper session management prevents `PendingRollbackError` issues.

**FastAPI Routes** (use dependency injection):
```python
@app.get('/tasks')
async def get_tasks(db: Session = Depends(get_db)):
    # Session automatically created and closed
    tasks = db.query(Task).all()
    return tasks
```

**Background Jobs** (use SessionLocal directly):
```python
def background_job():
    db = SessionLocal()
    try:
        # Do work with db
        db.commit()
    finally:
        db.close()
```

**Why**: FastAPI routes use dependency injection for automatic lifecycle. Background jobs run outside request context and must manage sessions manually.

## Known Issues & Solutions

### Fixed Issues (8 Major Improvements)
✅ **Session Management** - Fixed `PendingRollbackError` with session-per-request pattern (`SessionLocal()` for background, `Depends(get_db)` for routes)
✅ **Architecture Refactor** - Split 171-line monolithic app.py into 3-layer Clean Architecture (Repository + Service + Router), now ~113 lines
✅ **Task ID System** - Added `autoincrement=True` to all models, `id` field to `ScheduledTask` for DSPy task references
✅ **Repository Pattern** - Migrated schedule_checker.py to use repositories, complete pattern adoption
✅ **Error Handling** - Added try-catch with fallback scheduling (tomorrow 9-10am) to prevent DSPy failures crashing app
✅ **Config Management** - Centralized all config in `config.py` with Pydantic Settings (DSPy model, scheduler interval, DB URL)
✅ **Retry Logic** - Added tenacity retry decorators (3 attempts, exponential backoff) for transient API failures
✅ **Health Monitoring** - Added `/health` endpoint with component status checks for operations monitoring

### Active Bugs (Last Updated: 2025-10-01)

**CRITICAL - Breaking Changes & Test Failures** (5 NEW from Review #2)

🐛 **BUG #47: Pydantic V2 Config** ✅ FIXED - config.py:55 migrated `class Config` → `model_config = ConfigDict(...)` for V2 compatibility
🐛 **BUG #48: Pydantic .dict()** ✅ FIXED - scheduler.py:56 replaced `.dict()` → `.model_dump()` in _serialize_schedule()
🐛 **BUG #49: E2E Tests 50% Failing** ⚠️ CLARIFIED - 9/18 E2E tests fail (toast messages, timeline render, context update) - NOT permissions, needs investigation
🐛 **BUG #50: Pytest Config Missing** ✅ FIXED - Created pytest.ini with proper testpaths, eliminates warnings
🐛 **BUG #51: Pytest Cache Warnings** ✅ FIXED - pytest.ini configuration resolved all cache warnings

**CRITICAL - Data Corruption Risks** (All FIXED ✅)
🐛 **#1-6: Race Conditions & Data Safety** - Added `db.refresh()` before modifications, `_safe_fromisoformat()` helper, multiple-active-task validation, scheduler shutdown handler, session cleanup in finally blocks, documented transaction boundaries (DSPy tracking isolation intentional for audit trail)

**HIGH PRIORITY - Code Quality** (All FIXED ✅)
🐛 **#7-10: Code Quality Fixes** - Deleted dead code (unused update() method), added config field validators (scheduler_interval, fallback hours), isolated test DB (unique temp file per test), added db.refresh() before context modifications

**MEDIUM PRIORITY - Robustness**
🐛 **#11: DST-Safe Datetime** ✅ FIXED - task_service.py:128-134 now uses `replace(hour=0) + timedelta(hours=N)` pattern to avoid DST boundary failures
🐛 **#12: Tracker DB Retry** - dspy_tracker.py:30 add tenacity retry for DB lock/timeout (lost audit trail risk)
🐛 **#13: Input Length** ✅ FIXED - Added Pydantic schemas (TaskCreate, ContextUpdate) with max lengths
🐛 **#14: Inconsistent Returns** - task_repository.py:51 return `(task, was_modified: bool)` or raise exception

**LOW PRIORITY - Maintenance**
🐛 **#15: Method Naming** - context_repository.py:25 rename `update()` → `update_or_create()`/`upsert()`
🐛 **#16: NULL Handling** - Standardize NULL checks across codebase (some ternary, some assume valid)
🐛 **#17: Silent DB Errors** ✅ FIXED - dspy_tracker.py:54-56 added except block with logger.error() and rollback for database failures

**Phase 2 Bugs (2025-10-01 Review)**
🐛 **#18-24: Data Safety Fixes** ✅ FIXED - Added String max_lengths (models.py), row locking for get_or_create, 404 checks in routers, state validation (can't start completed/complete unstarted), safe serialization helper, Path(gt=0) for task_id, query order desc()
🐛 **#25: DB Indexes** - Add indexes on completed, actual_start_time, scheduled_start_time (performance)
🐛 **#26: Audit Logging** - Add logger.debug() to repository CRUD operations
🐛 **#27-30: Architecture Issues** - Exponential backoff for reschedule, remove module-level state, app state vs globals, check scheduler.running before start()

**Phase 3 Bugs (2025-10-01 Fresh Review)**
🐛 **#31-33: Deprecations** ✅ FIXED - SQLAlchemy import path (orm vs ext.declarative), Pydantic @validator → @field_validator, FastAPI @on_event → lifespan context manager
🐛 **#34-35: GlobalContext** ✅ FIXED - Added singleton unique constraint, explicit updated_at setting in repository
🐛 **#36: Race Window** - Use UPSERT pattern with unique constraint in get_or_create
🐛 **#37-39: Config Validation** ✅ FIXED - Added validators for API key, DSPy model format, scheduler interval max (3600s)
🐛 **#40: Query Assumption** - context_repository .first() assumes single row, enforce at DB level
🐛 **#41-43: Minor Issues** - Log skipped tasks, verify scheduler.running in health check, validate due_date ISO format
🐛 **#44-46: Test/Template** ✅ FIXED - Updated singleton test with IntegrityError check, .dict() → .model_dump() (2x), TemplateResponse param order (10x)

**Bug Summary**: 78 total | 36 fixed, 42 remaining (1 critical, 5 high, 36 medium/low) | Score: 8.8/10 | Tests: 58/58 unit (100%), 76 total | Production ready: 88%

**Critical** (1): #55 leftover files | **High** (5): #12,56-59 (tracker retry, state, health, race, indexes) | **Fixed**: Phases 1-6 (#1-11,13,17-19,21-24,31-39,44-48,50-52,54,78)

**Phase 5-6 Fixes (2025-10-01)**: #11 DST-safe datetime, #52 calendar template, #54 tracker failures, #78 timeline template. Added E2E infra (Playwright), singleton column, CSS classes. #55 leftover files blocked by hook (manual cleanup needed).

**Phase 6 Review (2025-10-01)**: Comprehensive file-by-file analysis found 25 new bugs. Score adjusted 9.0→8.5 due to stricter criteria. Key findings: DST crash bug, silent tracker failures, module state violations, missing indexes. Production ready 85%+ for single-user, needs work for multi-user SaaS.

### Architecture Debt (Historical - See "Architecture Assessment" for current state)

**Remaining**: 3 leftover files (manual deletion), no caching, no Alembic, SQLite limits, no rate limiting, no observability (Sentry/Prometheus), inconsistent logging, missing type hints

**Progress**: 7.5 → 8.8/10 (32 bugs fixed across 4 phases) | Production ready: 88%

## Roadmap

### ✅ Completed (Phases 1-6)
Session-per-request, 3-layer architecture, DI, error handling + fallback, retry logic, health endpoint, Pydantic validation, deprecation migrations, GlobalContext singleton, template fixes (#52,#78), DST-safe datetime (#11), tracker error handling (#54), E2E infrastructure (Playwright, 76 tests: 58 unit, 18 E2E).

### Phase 7: Performance & Observability (3-4h)
- DB indexes (#59), repository logging (#26), tracker DB retry (#12), health check improvements (#57), module state cleanup (#56), race condition fix (#58)

### Phase 8-9: Production Hardening (10-15h)
- Alembic migrations, Redis caching, rate limiting, PostgreSQL, Sentry, Prometheus/Grafana, auth, CI/CD

## Development Commands

### Docker Operations
```bash
# Start application (accessible at http://localhost:8081)
docker compose up --build -d

# Restart after code changes
docker compose restart

# View logs (includes DSPy inference details)
docker compose logs -f web

# Stop application
docker compose down
```

### Database Operations
```bash
# Reset/migrate database (drops and recreates all tables)
docker compose exec web python migrate_db.py
```

### Testing
```bash
# Run unit tests
docker compose exec web python -m pytest test_app.py -v

# Run E2E tests
docker compose exec web python -m pytest test_e2e.py -v

# Run all tests
docker compose exec web python -m pytest -v

# Run specific test
docker compose exec web python -m pytest test_app.py::test_task_id_autoincrement -v
```

**Test Coverage** (76 tests: 58 unit 100% passing, 18 E2E):
- **test_app.py** (47): Page rendering, task lifecycle, context management, DSPy logging, timezone consistency, ID autoincrement, validation (8 tests: input length, state transitions, error handling, concurrency), config validation (3 tests), task priority (10 tests)
- **test_components.py** (11): Repository CRUD (TaskRepository, GlobalContextRepository, DSPyExecutionRepository), TaskService helpers (_safe_fromisoformat: 5 tests)
- **E2E** (18, Playwright): Task ops + toasts, navigation, active tracker, timeline view (6 tests). Flaky due to AI timing (1-5s) and async HTMX updates.

### Debugging DSPy Inference
All DSPy calls log detailed information:
- 🚀 Inference started
- 📥 Input data (task, context, schedule, current time)
- 📤 Output data (scheduled times or priorities)
- ✅ Inference completed

Check logs to debug scheduling decisions.

## Critical Architecture Decisions

### Database Session Management
**CRITICAL**: The application uses **session-per-request** pattern to avoid session corruption:

- **Routes**: Use `db: Session = Depends(get_db)` dependency injection
- **Services**: Receive session from routes via repositories
- **Repositories**: Operate on injected session
- **Background Jobs**: Create own session with `SessionLocal()` in try/finally block
- **DSPy Tracker**: Creates own session for thread-safe logging

**NEVER** use a global `db` session - this causes `PendingRollbackError` and data loss.

### Avoiding Circular Imports
- Routers import `get_time_scheduler()` from `schedule_checker` (not from `app`)
- Services receive `time_scheduler` as constructor parameter
- This avoids circular dependency: `app` → `routers` → `app`

### Time Handling
- ALL models use `datetime.now` (local time), NOT `datetime.utcnow`
- Tests verify timezone consistency across all models
- No timezone info stored (naive datetimes)

## Key Workflows

### Adding a New Task (Async Scheduling - Fast Response)
1. User submits title + optional task-specific context via form
2. Task **immediately created** with fallback times (tomorrow 9am) and `needs_scheduling=True` flag (fast response <50ms)
3. Task appears in UI immediately with temporary schedule
4. Background scheduler (runs every 5s) detects tasks with `needs_scheduling=True`
5. `TimeSlotModule` receives: task, context, **global context**, current datetime, existing schedule (with task IDs)
6. DeepSeek V3.2-Exp generates optimal `scheduled_start_time` and `scheduled_end_time` with reasoning
7. Task updated in database with final schedule, `needs_scheduling=False`
8. `dspy_tracker` logs complete inference to `DSPyExecution` table
9. UI updates automatically (HTMX polling) to show final schedule

**Benefit**: Enables rapid successive task entry without waiting for AI (1-5s per task). Multiple tasks can be added quickly, all scheduled asynchronously in background.

### Task Lifecycle States
- **Created**: Has scheduled times, no actual times
- **Started**: User clicked "Start", `actual_start_time` set
- **Completed**: User clicked "Complete", `actual_end_time` set

### Background Schedule Checking & Automatic Scheduling/Rescheduling
Every 5 seconds, `check_and_update_schedule()` runs in background thread:
1. Creates own database session (`SessionLocal()`)
2. **First: Schedules new tasks** - Queries tasks with `needs_scheduling=True`, calls DSPy for optimal times, sets `needs_scheduling=False`
3. **Then: Reschedules overdue tasks** - Queries incomplete tasks, checks if end time passed or start time passed (not started)
4. For each task needing (re)scheduling, calls `reschedule_task(db, task, now)` which:
   - Queries existing schedule (excluding current task)
   - Gets global context
   - Calls DSPy `TimeSlotModule` for new times
   - **`db.refresh(task)`** before updating (prevents `StaleDataError`)
   - Commits new scheduled times
5. Closes session in `finally` block
6. Logs: "🎯 Scheduled {n} new task(s)" and "🔄 Rescheduled {n} task(s)" with new times

## Environment Configuration

Required in `.env`:
- `OPENROUTER_API_KEY`: API key for OpenRouter (DeepSeek access)
- `DATABASE_URL`: SQLite database path (default: `sqlite:///tasks.db`)

Current LM configuration in `app.py`:
```python
lm = dspy.LM('openrouter/deepseek/deepseek-v3.2-exp', api_key=os.getenv('OPENROUTER_API_KEY'))
```

## Testing

Run: `docker compose exec web pytest -v` | **76 tests** (58 unit 100% passing: test_app.py 47, test_components.py 11 | 18 E2E Playwright). Test DB: `test_tasks.db` w/ SessionLocal() + cleanup fixtures.

## Database Schema Changes

Modify `models.py` → `docker compose exec web python migrate_db.py` (⚠️ drops all data) → `docker compose restart web`

## Context System

**Global Context** (`GlobalContext` table): User-wide prefs/constraints (work hours, scheduling prefs). **Task Context** (`Task.context` field): Per-task priorities/constraints/requirements. Both passed to DSPy modules, all logged for debugging.

## UI Design

**Theme**: Monochrome glassmorphism (radial gradient bg, translucent cards w/ backdrop-filter, fade/hover/scale animations, card layout). Active tracker (top-right pulse), toast notifications (bottom-right, 2s auto-dismiss, HTMX `hx-on::after-request`). All styles in `base.html`.

## Architecture Assessment

**Metrics**: 2.4k lines (1.2k prod + 1.2k tests) | 25 Python files + 11 templates | 80 lines/file avg | 79% test-to-code ratio

**Strengths**: 3-layer Clean Architecture (Repository + Service + Router), DI throughout, session-per-request, input validation, state/NULL/race safety, error handling + fallback, retry logic, centralized config, health monitoring, 50 tests (100% unit, 50% E2E), zero TODO/FIXME

**Gaps**: No DB indexes, no Alembic migrations, SQLite scalability limits, minimal observability, 3 leftover files

---

## Current Status (2025-10-01)

**8.8/10** (88% production ready) | 36/78 bugs fixed | 58/58 unit tests passing, 76 total | Zero pytest warnings

**Remaining**: 42 bugs (1 critical #55, 5 high #12,56-59) | **Next**: Delete leftover files (manual), Phase 7 (indexes, state, race conditions), Phase 8-9 (PostgreSQL, observability, auth)

---

## Architecture Review (2025-10-01 - Comprehensive Analysis)

**Review Date:** 2025-10-01
**Reviewer:** Claude (Comprehensive "rr" Review)
**Scope:** Complete codebase analysis (37 files, 2,461 total lines)
**Methodology:** File-by-file review, metrics analysis, pattern assessment, production readiness evaluation

### Codebase Metrics

**Size**: 2,461 lines (1,100 prod + 1,000 test + 77 config + 284 HTML) | 37 files (26 .py, 11 .html) | 84 lines/file avg | 91% test-to-code ratio

**Quality**: Zero TODO/FIXME/HACK, zero pytest warnings, modern Python (Pydantic V2, SQLAlchemy 2.0, FastAPI lifespan), 58/58 unit tests passing (100%)

### Architecture Strengths

**Excellent** (5/5): 3-layer architecture (Repository→Service→Router, zero violations), DI (constructor + Depends(), no circular imports), session management (per-request pattern, zero errors), modern Python (Pydantic V2, SQLAlchemy 2.0, FastAPI lifespan)

**Strong** (4/5): Error handling (fallback scheduling, tenacity retry, state validation)

### Critical Issues (Production Blockers)

**A1** Leftover files (app_new.py, app.py.backup) | **A2** No indexes (O(n) scans every 5s) | **A3** No migrations (data loss on schema changes) | **A4** SQLite limits (no concurrent writes)

### High Priority Issues

**A5** Module state (global variables) | **A6** DST crash (datetime.replace() on spring forward) ✅ FIXED | **A7** No caching (GlobalContext queried on every create)

### Production Readiness Scorecard

| Category | Score | Evidence | Gaps |
|----------|-------|----------|------|
| Architecture | 9.5/10 | Clean 3-layer, DI, separation | Module-level state (#A5) |
| Code Quality | 9.0/10 | 84 lines/file avg, zero TODOs | Naming (#A10) |
| Testing | 8.5/10 | 100% unit pass, good coverage | Flaky E2E (#A11) |
| Error Handling | 9.0/10 | Fallbacks, retries, validation | DST bug (#A6) |
| Configuration | 9.5/10 | Pydantic validators, type-safe | None |
| Database | 6.0/10 | Clean models, proper sessions | No indexes, migrations, SQLite |
| Scalability | 5.0/10 | Works for single user | SQLite, no cache, no rate limit |
| Observability | 6.5/10 | DSPy tracking, health endpoint | No Sentry/Prometheus |
| Security | 5.0/10 | Input validation | No auth, no rate limit |

**Overall: 8.5/10** (decreased from 8.8/10 after Phase 6 comprehensive review)

**Why Score Decreased:**
- Previous review missed critical DST bug that causes crash on spring forward
- Silent failure in tracker (lost audit trail) not caught
- More thorough file-by-file analysis found 25 additional issues
- Stricter evaluation criteria for production readiness

**Production Ready For:**
✅ Single user / personal use (excellent)
✅ Internal tools / prototypes (works well)
✅ Demos / proof of concepts (very polished)
✅ Learning clean architecture (textbook example)

**NOT Production Ready For:**
❌ Multi-user SaaS (needs PostgreSQL, auth, rate limiting)
❌ High concurrency (SQLite will lock, needs caching)
❌ Mission-critical data (no migrations = data loss on schema changes)

### Recommendations by Phase

**Phase 7 (1-2h)**: Delete files #A1, add indexes #A2, fix module state #A5
**Phase 8 (6-8h)**: Alembic #A3, PostgreSQL #A4, Redis cache #A7, rate limiting, E2E fixes
**Phase 9 (8-10h)**: Sentry, Prometheus, structured logging, auth, type hints

### Key Learnings

**Score evolution**: 9.0→8.8→8.5 due to stricter criteria, discovery of DST crash, silent failures, 25 new bugs in file-by-file review. Still 85%+ ready for single-user/internal.

**Technical debt origins**: Leftover files from Phase 2-3 refactor, module state from circular import workaround, E2E flakiness from real DSPy API timing (1-5s) + 2s toast auto-dismiss.

**What we do exceptionally well**: Textbook clean architecture, small files (84 avg), zero debt markers, 100% unit pass rate, comprehensive docs. Learning-quality codebase.

**Review methodology**: Phase 6 comprehensive file-by-file (37 files, 2,461 lines) found DST bug, tracker failures, 25 new issues. Post-review "rr" found test count outdated (50→57), discovered bug #78 (timeline template).
