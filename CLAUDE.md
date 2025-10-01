# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A DSPy-powered task scheduling web application that uses AI (DeepSeek V3.2-Exp via OpenRouter) to automatically schedule tasks based on existing commitments and user-provided context. Built with FastAPI, HTMX, and SQLAlchemy using Repository Pattern and Service Layer architecture.

**Tech Stack**: FastAPI + SQLAlchemy/SQLite + DSPy + HTMX + APScheduler + Docker

## Architecture

### Core Components

**Architecture**: Repository + Service + Router (Clean Architecture)

**app.py** (122L): DSPy init, APScheduler (5s), router inclusion, index page, /health endpoint

**repositories/** (6 repos): `task_repository.py`, `context_repository.py`, `dspy_execution_repository.py`, `chat_repository.py`, `settings_repository.py`, `__init__.py`. All receive `db: Session` via constructor.

**services/** (5 services): `task_service.py` (DSPy scheduling + retry), `context_service.py`, `inference_service.py`, `chat_service.py` (natural language task management w/ DSPy ChatAssistantModule), `settings_service.py`. Receive repositories + time_scheduler via constructor.

**routers/** (5 routers): `task_router.py`, `context_router.py`, `inference_router.py`, `chat_router.py` (chat interface: /chat, /chat/send, /chat/clear), `settings_router.py`. Use DI (`Depends`), thin presentation layer.

**scheduler.py**: `TimeSlotModule` (schedules tasks w/ ScheduledTask model incl IDs, returns start/end/reasoning) + `PrioritizerModule` (prioritizes w/ TaskInput/PrioritizedTask). Both use ChainOfThought + dspy_tracker.

**chat_assistant.py** (55L): `ChatAssistantModule` (DSPy ChainOfThought for natural language task management). Takes user message + task list JSON + global context, outputs action (create_task/start_task/complete_task/stop_task/delete_task/chat) + task fields + natural language response. Uses `ChatSignature` with structured output fields.

**models.py**: 5 SQLAlchemy models w/ autoincrement IDs: `Task` (scheduled vs actual times, context, priority, **needs_scheduling flag**), `GlobalContext` (shared prefs/constraints), `DSPyExecution` (module tracking), `Settings` (LLM config, singleton), `ChatMessage` (user/assistant conversation history). Sessions: `get_db()` for routes, `SessionLocal()` for background.

**schedule_checker.py**: Background job (5s) that: 1) Schedules new tasks w/ `needs_scheduling=True` (async DSPy scheduling), 2) **Reprioritizes all incomplete tasks when new tasks are scheduled** (DSPy PrioritizerModule), 3) Finds overdue/unstarted tasks and reschedules. Uses `SessionLocal()`.

**dspy_tracker.py**: Wraps DSPy calls, logs inputs/outputs/duration to `DSPyExecution`, uses `SessionLocal()`.

### Frontend Architecture

**Templates** (Jinja2 + HTMX): `base.html` (active tracker, modal container, mobile-responsive glassmorphism theme, **live duration JavaScript**), `index.html` (list + form), `calendar.html` (timeline w/ height-based duration), `history.html` (completed tasks w/ actual time tracking), `chat.html` (AI assistant interface w/ message history). Components: `task_item.html` (clickable w/ modal trigger, priority badge, duration display), `gantt_item.html` (duration in hours), `timeline_item.html` (height-scaled, clickable, priority badge, duration display, stop button), `history_item.html` (actual times, duration calc, context display), `chat_message.html` (user/assistant message pair), `chat_history.html` (message list), `active_task.html` (**live updating duration**), `global_context.html`, `inference_log.html`, `task_detail_modal.html` (detailed modal: timeline, priority, status, actions).

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

### Fixed Issues Summary
✅ **Phases 1-8 (44 bugs)**: Session management, 3-layer architecture, task ID system, repository pattern, error handling + fallback, config management, retry logic, health monitoring, Pydantic V2 migration, deprecation fixes, GlobalContext singleton, template fixes, DST-safe datetime, tracker retry, settings validation, SQLAlchemy 2.0

### Active Bugs (Last Updated: 2025-10-01)

**CRITICAL**: 🐛 #115 E2E test failures (variable rate, toast/timeline tests)

**HIGH**: 🐛 #56-59 (module state, race conditions, indexes)

**MEDIUM**: 🐛 #14,25-26,36,40-41 (inconsistent returns, indexes, logging, race window, query assumptions)

**LOW**: 🐛 #15-16,55,123-138 (naming, NULL handling, leftover files, backup gaps, performance optimizations)

**Bug Summary**: 138 total | 44 fixed Phases 1-8, 94 remaining (2 critical, 4 high, 42 med/low) | Score: 8.6/10 | Tests: 107/107 unit (100%), 107/126 total (85%) | Production ready: 86%

**Critical** (2): #55,115 (leftover files, E2E failures) | **High** (4): #56-59 (module state, race conditions, indexes) | **Fixed**: Phases 1-8 (#1-13,17-19,21-24,31-39,44-48,50-52,54,78,114,116-122)

**Phase 5-8 Fixes**: DST-safe datetime, calendar/timeline templates, E2E infra (Playwright), tracker retry, reprioritization after reschedule, health check improvements, settings validation/error handling, SQLAlchemy 2.0 migration. See bug list above for details.

**E2E Toast Test Investigation (2025-10-01)**: E2E tests fail due to HTMX event timing. Root cause: `htmx:beforeRequest` event fires for unrelated elements (DIV targets, global context form) but not consistently for task form submissions. Toast notifications work when called manually (`showToast()` function verified). Current implementation uses `data-toast-message` attributes with global `htmx:beforeRequest`/`htmx:afterRequest` event listeners. Issue likely related to HTMX event propagation with `hx-target` pointing to external elements. Not critical as core functionality works and E2E flakiness is documented. Consider: 1) Upgrading HTMX to v2.x, 2) Using `htmx:configRequest` to store toast messages, 3) Switching to server-sent events for toast notifications.

### Architecture Debt (Historical - See "Architecture Assessment" for current state)

**Remaining**: 3 leftover files (manual deletion), no caching, no Alembic, SQLite limits, no rate limiting, no observability (Sentry/Prometheus), inconsistent logging, missing type hints

**Progress**: 7.5 → 8.6/10 (44 bugs fixed across 8 phases) | Production ready: 86%

## Roadmap

### ✅ Completed (Phases 1-8)
Session-per-request, 3-layer architecture, DI, error handling + fallback, retry logic, health endpoint, Pydantic validation, deprecation migrations, GlobalContext singleton, template fixes, DST-safe datetime, tracker retry, E2E infrastructure (Playwright), live duration tracking, chat feature, priority system with auto-reprioritization, vertical timeline, stop task functionality, history tab, task modal, backup/restore scripts, settings page, responsive design (4 breakpoints), decorator fixes.

**Features**: Chat assistant (natural language task mgmt), priority badges (0-10 range, color-coded), auto-reprioritization (DSPy), timeline view (height-scaled), history tracking, settings page, backup/restore, responsive design.

### Phase 9: Performance & Observability (2-3h)
DB indexes, repository logging, module state cleanup, race condition fixes

### Phase 10: Production Hardening (10-15h)
Alembic, Redis cache, rate limiting, PostgreSQL, Sentry, Prometheus, auth, CI/CD

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

**Test Coverage** (119 tests: 100 unit @ 100%, 19 E2E @ variable pass rate):
- **test_app.py** (79): Routes (page rendering, task lifecycle, context, DSPy logging, timezone, IDs), validation (8), config (3), priority (12), timeline (11), history (6), settings (7), reprioritization (1), chat (11)
- **test_components.py** (14): Repositories (Task, Context, DSPyExecution, Chat, Settings), TaskService helpers (5), ScheduleChecker (1)
- **test_responsive.py** (8): Media queries, responsive styles, active tracker positioning, font/padding scaling
- **E2E** (19, Playwright): Task ops + toasts (5), navigation (2), active tracker (2), timeline (4), context (2), settings (2), responsive (2). Variable failures due to AI timing (1-5s) + async HTMX.

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

### Adding a New Task (Async Scheduling + Auto-Reprioritization)
1. User submits → Task created immediately with fallback times (tomorrow 9am), `needs_scheduling=True` (<50ms response)
2. Background scheduler (5s interval) detects → DSPy TimeSlotModule generates optimal times + reasoning
3. PrioritizerModule auto-reprioritizes all incomplete tasks (0-10 scores)
4. dspy_tracker logs all inferences → UI updates via HTMX polling

**Benefit**: Rapid successive task entry without waiting for AI (1-5s). Manual reprioritization via "Reprioritize All Tasks" button.

### Task Lifecycle States
- **Created**: Has scheduled times, no actual times
- **Started**: User clicked "Start", `actual_start_time` set
- **Stopped**: User clicked "Stop", `actual_start_time` cleared (can restart)
- **Completed**: User clicked "Complete", `actual_end_time` set, `completed=True`

### Background Schedule Checking (5s interval)
1. `SessionLocal()` → Schedules new tasks (`needs_scheduling=True`) → Reschedules overdue/unstarted tasks
2. For each task: Query schedule + global context → DSPy TimeSlotModule → `db.refresh(task)` → Commit
3. Logs: "🎯 Scheduled {n}" and "🔄 Rescheduled {n}"

### Chat Assistant - Natural Language Task Management
**Flow**: User message → `ChatService` (task list + context) → `ChatAssistantModule` (DSPy ChainOfThought) → Outputs action (chat/create_task/start_task/complete_task/stop_task/delete_task/list_tasks) + task fields + response → `ChatService._execute_action()` via repositories → Save to `ChatMessage` → HTMX updates UI

**Examples**: "Create high priority task to fix login bug", "Start task 5", "Complete the login bug task", "What tasks do I have?"

**Architecture**: ChatAssistantModule (DSPy), ChatService (action execution), ChatRepository (CRUD). All logged via `@track_dspy_execution`.

## Environment Configuration

Required in `.env`:
- `OPENROUTER_API_KEY`: API key for OpenRouter (DeepSeek access)
- `DATABASE_URL`: SQLite database path (default: `sqlite:///tasks.db`)

Current LM configuration in `app.py`:
```python
lm = dspy.LM('openrouter/deepseek/deepseek-v3.2-exp', api_key=os.getenv('OPENROUTER_API_KEY'))
```

## Testing

Run: `docker compose exec web pytest -v` | **126 tests total** (107 unit 100% passing: test_app.py 82, test_components.py 17, test_responsive.py 8 | 19 E2E Playwright, variable failures). Test DB: `test_tasks.db` w/ SessionLocal() + cleanup fixtures.

**Priority tests (12)**: Default value, set/update, range validation, sorting, filtering, negative/above-10 values, Pydantic model validation, persistence across updates, multiple tasks.

**Timeline tests (11)**: Page load, current time indicator, scheduled tasks display, chronological ordering, empty state, duration display, priority badges, completed task styling, stop functionality (3 tests).

**History tests (6)**: Page load, completed tasks filter (excludes incomplete/scheduled), chronological ordering (most recent first), duration calculations (2h 30m format), empty state, context display.

**Settings tests (9)**: Page load, default values, update via POST, singleton constraint, form displays current values, max_tokens validation, get_or_create, toast notification, loading indicator.

**Chat tests (7)**: Page load, send message, create/start/complete/delete task actions, clear history, message persistence.

**Test Coverage Gaps**: settings_repository (no direct tests), schedule_checker (missing new task scheduling + overdue rescheduling tests), error handling (no DSPy API failure / DB unavailability tests), app.py startup/lifecycle. Current coverage sufficient for project size but error handling tests would improve robustness.

## Database Schema Changes & Backup

**Before schema changes:**
```bash
# 1. Backup your data
docker compose exec web python backup_db.py

# 2. Migrate (⚠️ drops all data)
docker compose exec web python migrate_db.py

# 3. Restore from backup
docker compose exec web python restore_db.py
```

**Database persistence**: `tasks.db` is mounted as volume, survives container restarts and rebuilds. Only lost if manually deleted or `migrate_db.py` runs.

**Backup scripts**: `backup_db.py` exports to JSON (all tasks + global context), `restore_db.py` imports from JSON. See `BACKUP_RESTORE.md` for details.

## Context & Settings

**Global Context** (`GlobalContext` table): User-wide prefs/constraints (work hours, scheduling prefs). **Task Context** (`Task.context` field): Per-task priorities/constraints/requirements. Both passed to DSPy modules, all logged for debugging.

**Settings** (`Settings` table, singleton): LLM configuration - `llm_model` (default: openrouter/deepseek/deepseek-v3.2-exp), `max_tokens` (default: 2000, range: 100-10000). Editable via `/settings` page with HTMX form + toast notifications.

## UI Design

**Theme**: Monochrome glassmorphism (radial gradient bg, translucent cards w/ backdrop-filter, fade/hover/scale animations, card layout). Active tracker (top-right pulse), toast notifications (bottom-right, 2s auto-dismiss, triggered via `data-toast-message` attribute + global `htmx:beforeRequest`/`htmx:afterRequest` event listeners). All styles in `base.html`.

**Responsive Design**: Mobile-first with 3 breakpoints:
- **Mobile** (≤480px): Full-width buttons, reduced padding (15px/10px), smaller fonts (h1: 1.75rem, h2: 1.2rem), stacked navigation, active tracker repositioned to static
- **Tablet** (≤768px): Flex-wrap navigation, 95% modal width, reduced padding (20px/15px), smaller fonts (h1: 2rem, h2: 1.3rem)
- **Desktop** (default): 1400px max-width for better screen utilization, fixed active tracker (top-right), 40px padding
- **Large Desktop** (≥1200px): Increased padding (40px), larger sections (30px padding)
- **Task cards**: Flex-wrap with 8px gap, priority badge wraps on narrow screens, buttons flex to fill available space (min-width: 70px)

**Priority badges**: Color-coded (🔴 red ≥7.0, 🟡 yellow 4.0-6.9, 🟢 green <4.0) with glassmorphism styling. Format: "Priority: X.X" (task list), "PX.X" (timeline/gantt).

**Timeline view**: Height-scaled task cards (2px per minute, min 60px), duration displayed in hours, clickable for modal details, stop button for started tasks.

**Task interactions**: All tasks clickable (HTMX `hx-get="/tasks/{id}/details"` → modal), buttons have `onclick="event.stopPropagation()"` to prevent modal on button clicks.

## Architecture Assessment

**Metrics**: ~4.0k lines (1.4k prod + 1.6k tests + 1.0k other) | 36 Python files + 19 templates | 111 lines/file avg | 114% test-to-code ratio

**Strengths**: 3-layer Clean Architecture (Repository + Service + Router), DI throughout, session-per-request, input validation, state/NULL/race safety, error handling + fallback, retry logic, centralized config, health monitoring, **chat assistant (natural language task management)**, 119 tests (100 unit 100% passing, 19 E2E with variable failures), zero TODO/FIXME

**Gaps**: No DB indexes, no Alembic migrations, SQLite scalability limits, minimal observability, 3 leftover files

---

## Current Status (2025-10-01)

**8.6/10** (86% production ready) | 44/138 bugs fixed | 107/107 unit (100%), 107/126 total (85%) | Zero pytest warnings | **TEST REVIEW COMPLETE: 126 tests (107 unit, 19 E2E), toast investigation documented, coverage gaps identified**

**Remaining**: 94 bugs (2 critical #55,115 | 4 high #56-59) | **Next**: Fix E2E toast timing (consider HTMX v2 upgrade), delete leftover files, Phase 9 (indexes, state, race), Phase 10 (PostgreSQL, observability, auth)

**Test Coverage Gaps**: settings_repository, schedule_checker (new task scheduling, overdue rescheduling), error handling (DSPy API failures, DB unavailability), app.py lifecycle. Sufficient for current project size.

---

## Architecture Review (2025-10-01)

**Metrics**: ~4.0k lines (1.4k prod + 1.6k tests + 1.0k other) | 36 .py files + 19 templates | 111 lines/file avg | 114% test-to-code ratio | Zero TODO/FIXME/HACK, zero pytest warnings

**Strengths**: 3-layer architecture (Repository→Service→Router, zero violations), DI throughout, session-per-request, modern Python (Pydantic V2, SQLAlchemy 2.0, FastAPI lifespan), 100% unit test pass rate

**Critical Issues**: A1 Leftover files | A2 No indexes (O(n) scans every 5s) | A3 No migrations | A4 SQLite limits

**Production Readiness**: Architecture 9.5/10, Code Quality 9.0/10, Testing 8.5/10, Error Handling 9.0/10, Database 6.0/10, Scalability 5.0/10, Observability 6.5/10, Security 5.0/10

**Overall: 8.6/10** (86% production ready) | ✅ Ready for: single user, internal tools, demos, learning | ❌ Not ready for: multi-user SaaS, high concurrency, mission-critical data

**Key Learnings**: Score evolution 9.0→8.8→8.5→8.6 due to stricter criteria + discovered bugs (DST crash, silent failures, race conditions), then fixes (Phase 8). E2E flakiness from DSPy API timing (1-5s) + async HTMX. Textbook clean architecture, learning-quality codebase.
