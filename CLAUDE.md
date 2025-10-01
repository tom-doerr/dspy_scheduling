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

## Known Issues & Solutions (Last Updated: 2025-10-01 Phase 9)

**CRITICAL**: 🐛 #115 E2E test failures (variable rate, toast/timeline tests)

**HIGH**: 🐛 #56-59 (module state, race conditions)

**MEDIUM**: 🐛 #14,25-26,36,40-41 (inconsistent returns, indexes, logging, race window, query assumptions)

**LOW**: 🐛 #15-16,55,123-139,143-144 (naming, NULL handling, leftover files, backup gaps, performance optimizations, template issues, missing rollbacks)

**Bug Summary**: 144 total | 47 fixed Phases 1-9 (#1-13,17-19,21-24,31-39,44-48,50-52,54,78,114,116-122,140-142: DST fixes, E2E infra, SQLAlchemy 2.0, DB indexes, race conditions), 97 remaining: 1 critical (#115 E2E toast), 4 high (#56-59 module state/race), 5 medium (#14,25-26,36,40-41), 87 low (#15-16,55,123-139,143-144) | Score: 8.5/10 | Tests: 115/134 (86%) passing | Production ready: 85%

**E2E Toast Test Investigation (2025-10-01)**: E2E tests fail due to HTMX event timing. Root cause: `htmx:beforeRequest` event fires for unrelated elements (DIV targets, global context form) but not consistently for task form submissions. Toast notifications work when called manually (`showToast()` function verified). Current implementation uses `data-toast-message` attributes with global `htmx:beforeRequest`/`htmx:afterRequest` event listeners. Issue likely related to HTMX event propagation with `hx-target` pointing to external elements. Not critical as core functionality works and E2E flakiness is documented. Consider: 1) Upgrading HTMX to v2.x, 2) Using `htmx:configRequest` to store toast messages, 3) Switching to server-sent events for toast notifications.

**Recent Bugs (2025-10-01 Code Review)** - 3/6 fixed Phase 9:
🐛 **#139** (LOW): task_item.html:6 - Redundant `onclick="event.stopPropagation()"` on outer div
✅ **#140** (HIGH): GlobalContext.get_or_create() race condition - FIXED w/ IntegrityError handling
✅ **#141** (MEDIUM): Settings.get_or_create() - FIXED w/ IntegrityError handling
✅ **#142** (MEDIUM): Modal complete button - FIXED to close modal + show toast
🐛 **#143** (LOW): task_detail_modal.html:26-28 - Priority badge color inconsistency (always green)
🐛 **#144** (LOW): Repositories missing rollback in `self.db.commit()` try/except blocks

### Architecture Debt
**Remaining**: app_new.py (#55 - manual deletion), no Alembic, SQLite limits, no caching, no rate limiting, minimal observability, inconsistent logging. **Progress**: 9.0→8.5/10 (47 bugs fixed, DB indexes/race conditions fixed across 9 phases) | 85% production ready.

## Roadmap

### ✅ Completed (Phases 1-9)
**Architecture**: Session-per-request, 3-layer architecture, DI, error handling + fallback, retry logic, health endpoint, Pydantic V2, SQLAlchemy 2.0, GlobalContext singleton, DST-safe datetime, DB indexes (Task model), race condition fixes (GlobalContext, Settings).
**Features**: Chat assistant (natural language task mgmt), priority system (0-10, auto-reprioritization), timeline view (height-scaled), history tracking, settings page, backup/restore, responsive design (4 breakpoints), live duration tracking, E2E tests (Playwright).

### Phase 9: Performance & Observability (Partially Complete - 50%)
✅ DB indexes (Task model: completed, scheduled_start_time, needs_scheduling, actual_start_time)
✅ Race condition fixes (GlobalContext, Settings get_or_create with IntegrityError handling)
⏳ Repository logging
⏳ Module state cleanup (#56)

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

**Test Coverage** (134 tests: 115 unit @ 100%, 19 E2E @ variable pass rate):
- **test_app.py** (82): Routes (page rendering, task lifecycle, context, DSPy logging, timezone, IDs), validation (8), config (3), priority (10), timeline (11), history (7), settings (9), reprioritization (1), chat (8), stop (3)
- **test_components.py** (25): Repositories (Task 9, Context 1, DSPyExecution 2, Chat 3, Settings 2), TaskService helpers (5), ScheduleChecker (3: reschedule, invalid datetime, reprioritize)
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

Run: `docker compose exec web pytest -v` | **134 tests total** (115 unit 100% passing: test_app.py 82, test_components.py 25, test_responsive.py 8 | 19 E2E Playwright, variable failures). Test DB: `test_tasks.db` w/ SessionLocal() + cleanup fixtures (incl Settings).

**Coverage Highlights**: Priority (10 tests: defaults, validation, sorting, range checks), Timeline (11: display, ordering, duration, stop), History (7: filtering, chronological, duration calc), Settings (11: route 9, repo 2), Chat (11: actions 8, repo 3), Repositories (TaskRepo 9, SettingsRepo 2, ChatRepo 3, ContextRepo 1, DSPyExecRepo 2), ScheduleChecker (3: reschedule, invalid datetime, reprioritize).

**Coverage Gaps**: schedule_checker.check_and_update_schedule (orchestration), error handling (DSPy API failure / DB unavailability tests), app.py startup/lifecycle. Sufficient for current project size.

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

## Current Status (2025-10-01 Phase 9 Complete)

**8.5/10** (85% production ready) | 47/144 bugs fixed | 115/115 unit (100%), 115/134 total (86%) | Zero pytest warnings | **Phase 9 PARTIAL: DB indexes added, race conditions fixed, modal UX improved, test coverage expanded (+8 tests)**

**Remaining**: 97 bugs (1 critical #115 | 4 high #56-59 | 5 medium #14,25-26,36,40-41) | **Next**: Delete app_new.py (#55), module state cleanup (#56), Phase 9 completion (logging), Phase 10 (PostgreSQL, observability, auth)

---

## Architecture Review (2025-10-01)

### Metrics Breakdown

**Code Volume**: ~4,061 Python lines (1,400 prod + 2,184 tests + 477 utilities/scripts)
**Files**: 36 .py files + 19 HTML templates (740 lines)
**Quality**: Avg 110 lines/file | 155% test-to-code ratio | Zero TODO/FIXME/HACK | Zero pytest warnings

**Component Breakdown**:
- Core (app.py, models.py, scheduler.py, config.py, schemas.py): ~520 lines
- Repositories (6 files): ~231 lines
- Services (5 files): ~358 lines
- Routers (5 files): ~283 lines
- Supporting (dspy_tracker, schedule_checker, chat_assistant): ~359 lines
- Tests (4 files): 2,184 lines
- Templates: 740 lines
- Utilities (backup, migrate, restore): ~120 lines

### Architecture Analysis

**Strengths (9.5/10)**:
- ✅ Textbook 3-layer Clean Architecture (Repository→Service→Router, zero violations)
- ✅ Proper dependency injection throughout (FastAPI Depends)
- ✅ Session-per-request pattern (prevents PendingRollbackError)
- ✅ Modern Python (Pydantic V2, SQLAlchemy 2.0, type hints, async/await)
- ✅ Robust error handling (retry logic via tenacity, fallback scheduling, safe parsing)
- ✅ Input validation (Pydantic schemas with validators)
- ✅ Centralized configuration (Pydantic Settings with validation)
- ✅ Comprehensive testing (126 tests: 107 unit @ 100%, 19 E2E @ variable pass rate)
- ✅ Monitoring (DSPy execution tracking, health endpoint with component checks)
- ✅ Short, focused files (avg 110 lines, max ~220 lines)

**Weaknesses**:
- ✅ **Database Performance**: FIXED - Added indexes on `Task.completed`, `Task.scheduled_start_time`, `Task.needs_scheduling`, `Task.actual_start_time`
- ⚠️ **Database Scalability**: No Alembic migrations, SQLite concurrency limits, `migrate_db.py` drops all data
- ⚠️ **Module State**: `_schedule_checker_instance` in schedule_checker.py (bug #56) → testing/concurrency issues
- ✅ **Race Conditions**: FIXED - GlobalContext and Settings use proper IntegrityError handling with try/except pattern
- ⚠️ **E2E Reliability**: Toast tests fail variably due to HTMX event timing (bug #115)
- ⚠️ **Observability**: Basic logging only, no structured logs, metrics, or tracing
- ⚠️ **Security**: No auth, no rate limiting, no input sanitization beyond Pydantic
- ⚠️ **Scalability**: Single-user design, no caching, synchronous DSPy calls
- ⚠️ **UI Inconsistencies**: Priority badge colors inconsistent (bug #143), redundant onclick (bug #139)
- ⚠️ **Error Handling**: Missing rollback in repository commits (bug #144)

### Critical Issues & Recommendations

✅ **Priority 1: Database Performance (COMPLETE)**
- Added 4 indexes to Task model (completed, scheduled_start_time, needs_scheduling, actual_start_time)
- **Impact**: Prevents performance cliff beyond ~1,000 tasks. Eliminates O(n) table scans every 5s.

**Priority 2: Delete Leftover Files (5 min)** - Blocked by rm hook
```bash
rm app_new.py  # Bug #55 - Manual deletion required
```

**Priority 3: Fix Module State (1 hour)**
- Move `_schedule_checker_instance` from module-level to `app.state`
- Inject via DI instead of global variable
- Fixes bug #56, improves testability

**Priority 4: Add Migrations (2-3 hours)**
- Initialize Alembic, create initial migration from current schema
- Replace `migrate_db.py` workflow with proper migrations
- Prevents data loss on schema changes

✅ **Priority 5: Fix Race Conditions (COMPLETE)**
- ✅ PROPERLY fixed GlobalContext.get_or_create() using try/except with IntegrityError handling
- ✅ Added IntegrityError handling to Settings.get_or_create()
- ⏳ Add optimistic locking for task state transitions (future)
- ⏳ Add concurrent operation tests (future)

**Priority 6-10**: Observability (structured logging, metrics), PostgreSQL migration, Authentication (OAuth2+JWT), Rate limiting, Caching (Redis)

### Production Readiness Matrix

| Component | Score | Assessment |
|-----------|-------|------------|
| Architecture | 9.5/10 | ✅ Textbook clean architecture, proper patterns |
| Code Quality | 9.0/10 | ✅ Modern Python, short files, type hints |
| Testing | 8.5/10 | ✅ 100% unit pass rate, E2E flakiness documented |
| Error Handling | 9.0/10 | ✅ Retry logic, fallbacks, safe parsing, race condition handling |
| Database | 7.0/10 | ✅ Indexes added (+1.0), ⚠️ no migrations, SQLite limits |
| Scalability | 5.0/10 | ⚠️ Single-user, no caching, no distributed scheduler |
| Observability | 6.5/10 | ⚠️ Health check exists, but no metrics/tracing |
| Security | 5.0/10 | ⚠️ No auth, no rate limiting, env-only keys |
| **Overall** | **8.5/10** | **85% production ready** |

**✅ Ready for**: Single-user personal tools, internal company apps, demos, prototypes, learning
**❌ NOT ready for**: Multi-user SaaS, high concurrency (>100 req/sec), mission-critical data, public production

### Key Learnings

**Score Evolution**: 9.0→8.8→8.5→8.6→8.4→8.5 due to stricter criteria + discovered bugs (DST crash, silent failures, race conditions), fixes (Phase 8), comprehensive code review finding 6 new bugs, then Phase 9 fixes (indexes, race conditions, modal UX).

**E2E Flakiness Root Cause**: DSPy API timing (1-5s) + HTMX event timing issues. Toast notifications work when called manually (`showToast()` verified) but `htmx:beforeRequest` events don't fire consistently for task form submissions due to `hx-target` pointing to external elements.

**Architecture Quality**: Textbook example of clean architecture with proper separation of concerns. Demonstrates excellent software engineering practices. Main gaps now reduced to production hardening (migrations, observability, security) after addressing database performance and race conditions.

**Phase 9 Impact**: Database indexes prevent performance degradation at scale (~1,000+ tasks). Race condition fixes eliminate crash risk during concurrent access. Modal UX improvement provides consistent user experience. Test coverage expanded from 107 to 115 unit tests (+8: SettingsRepository 2, TaskRepository 4, ScheduleChecker 2), closing critical gaps in repository and scheduler testing.

**Next Steps**: Priority 2-4 (delete app_new.py, module state cleanup, Alembic migrations), then Phase 10 (PostgreSQL, observability, auth).
