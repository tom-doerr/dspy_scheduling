# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A DSPy-powered task scheduling web application that uses AI (DeepSeek V3.2-Exp via OpenRouter) to automatically schedule tasks based on existing commitments and user-provided context. Built with FastAPI, HTMX, and SQLAlchemy using Repository Pattern and Service Layer architecture.

**Tech Stack**: FastAPI + SQLAlchemy/SQLite + DSPy + HTMX + APScheduler + Docker

## Architecture

### Core Components

**app.py**: FastAPI application (~53 lines) with router-based structure:
1. DSPy module initialization (PrioritizerModule, TimeSlotModule)
2. Background scheduler initialization (APScheduler running every 5 seconds)
3. Router inclusion (task_router, context_router, inference_router)
4. Index page route

**Architecture Pattern**: Repository + Service Layer + Router (Clean Architecture)

**repositories/**: Data access layer (~130 lines total):
- `task_repository.py` (63 lines): Task CRUD operations, queries for incomplete/scheduled/active tasks
- `context_repository.py` (34 lines): Global context operations
- `dspy_execution_repository.py`: DSPy execution log queries
- All repositories receive `db: Session` via constructor, no direct session creation

**services/**: Business logic layer (~120 lines total):
- `task_service.py` (84 lines): Task operations with DSPy scheduling integration
- `context_service.py`: Global context management
- `inference_service.py`: DSPy execution log retrieval
- Services receive repositories and time_scheduler via constructor

**routers/**: Presentation layer (~130 lines total):
- `task_router.py` (70 lines): Task CRUD endpoints, uses `Depends(get_task_service)`
- `context_router.py` (28 lines): Global context endpoints
- `inference_router.py`: DSPy execution log endpoints
- Routers use dependency injection to get services, remain thin (presentation only)

**scheduler.py**: Two DSPy modules using ChainOfThought with Pydantic models:
- `TimeSlotModule`: Schedules new tasks by analyzing existing schedule + global context + task context + current time
  - Uses `ScheduledTask` model for type-safe task scheduling (includes id, title, start_time, end_time)
  - Task IDs allow DSPy to reference specific tasks in the schedule
  - Returns `start_time`, `end_time`, and `reasoning` for scheduling decisions
  - Integrated with dspy_tracker for execution logging
- `PrioritizerModule`: Prioritizes existing tasks based on urgency/importance and global context
  - Uses `TaskInput` and `PrioritizedTask` models for structured data
  - Integrated with dspy_tracker for execution logging

**models.py**: SQLAlchemy ORM with three models:
- `Task`: Task model with critical time distinctions:
  - `id`: Integer primary key with autoincrement (unique, continually incrementing)
  - `scheduled_start_time/scheduled_end_time`: AI-planned times
  - `actual_start_time/actual_end_time`: User-tracked times
  - `context`: Task-specific context for DSPy scheduling
  - `priority`: Calculated priority score
- `GlobalContext`: User's global priorities, constraints, and preferences (shared across all tasks)
  - `id`: Integer primary key with autoincrement
- `DSPyExecution`: Tracks all DSPy module executions (module name, inputs, outputs, duration)
  - `id`: Integer primary key with autoincrement
- Database session management:
  - `get_db()`: Generator for dependency injection in FastAPI routes
  - `SessionLocal()`: Direct session creation for background jobs

**schedule_checker.py**: Background job (runs every 5 seconds) that:
- Identifies tasks past their end time but incomplete
- Identifies tasks past their start time but not started
- **Automatically reschedules** using DSPy `TimeSlotModule`
- Uses `SessionLocal()` for proper session management in background context
- Logs detailed rescheduling information

**dspy_tracker.py**: DSPy execution tracker that:
- Wraps DSPy module calls to track inputs, outputs, and duration
- Stores all executions in `DSPyExecution` table
- Uses `SessionLocal()` for database operations (not dependency injection)
- Provides detailed logging for debugging

### Frontend Architecture

Templates use Jinja2 + HTMX for dynamic updates:
- `base.html`: Contains active task tracker (fixed top-right, updates every 5s), monochrome black/white glassmorphism theme
- `index.html`: Task list view with add form, global context editor
- `calendar.html`: Gantt chart timeline view
- Component templates: `task_item.html`, `gantt_item.html`, `active_task.html`, `global_context.html`, `inference_log.html`

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

### Fixed Issues
✅ **Database Session `PendingRollbackError`** (FIXED 2025-10-01):
- **Problem**: Background jobs and dspy_tracker used global `db` session causing transaction rollback errors
- **Solution**: Migrated to `SessionLocal()` in background jobs and dspy_tracker, `Depends(get_db)` in routes
- **Files changed**: `schedule_checker.py`, `dspy_tracker.py`, `app.py`

✅ **Monolithic app.py** (FIXED 2025-10-01):
- **Problem**: All routes in single 171-line file, business logic mixed with routes
- **Solution**: Split into Clean Architecture with Repository + Service + Router layers
- **Files created**:
  - `repositories/` (task_repository.py, context_repository.py, dspy_execution_repository.py)
  - `services/` (task_service.py, context_service.py, inference_service.py)
  - `routers/` (task_router.py, context_router.py, inference_router.py)
- **Result**: `app.py` now ~53 lines, excellent separation of concerns

✅ **Task ID System** (FIXED 2025-10-01):
- **Problem**: Task IDs needed explicit autoincrement configuration
- **Solution**: Added `autoincrement=True` to all model IDs (Task, GlobalContext, DSPyExecution)
- **Enhancement**: Updated `ScheduledTask` Pydantic model to include `id` field
- **Benefit**: DSPy modules can now reference specific tasks by ID
- **Files changed**: `models.py`, `scheduler.py`, `app.py`, `schedule_checker.py`

✅ **Background Scheduler Repository Migration** (FIXED 2025-10-01):
- **Problem**: `schedule_checker.py` used direct DB queries instead of repositories
- **Solution**: Updated to instantiate `TaskRepository` and `GlobalContextRepository`, use `get_incomplete()` method
- **Files changed**: `schedule_checker.py`
- **Result**: Complete repository pattern adoption throughout application

✅ **Basic Error Handling** (FIXED 2025-10-01):
- **Problem**: Services had zero try-catch blocks, DSPy failures crashed requests
- **Solution**: Added error handling to `task_service.py` `create_task()` with fallback scheduling
- **Fallback Behavior**: If DSPy fails, tasks scheduled for tomorrow 9am-10am
- **Files changed**: `services/task_service.py`
- **Result**: Application remains functional even when AI scheduling fails

✅ **Configuration Management** (FIXED 2025-10-01):
- **Problem**: Hardcoded values scattered (DSPy model, scheduler interval, DB URL)
- **Solution**: Created `config.py` with Pydantic Settings
- **Files changed**: `config.py` (new), `app.py`, `models.py`, `services/task_service.py`
- **Result**: Single source of truth for all configuration

✅ **Retry Logic for DSPy** (FIXED 2025-10-01):
- **Problem**: AI calls failed on rate limits/network issues without retry
- **Solution**: Added tenacity retry decorators (3 attempts, exponential backoff)
- **Files changed**: `services/task_service.py`, `schedule_checker.py`, `requirements.txt`
- **Result**: Resilient to transient API failures

✅ **Health Check Endpoint** (FIXED 2025-10-01):
- **Problem**: No way to monitor app health or DSPy API status
- **Solution**: Added `/health` endpoint with component health checks
- **Files changed**: `app.py`
- **Result**: Operations can monitor application health

### Architecture Debt

**CRITICAL Issues**:
1. ⚠️ **Duplicate Files**: `app_new.py` is identical to `app.py` (leftover from migration) - requires manual deletion

**HIGH Priority Issues**: (All fixed as of Phase 2)

**MEDIUM Priority Issues**:
2. ⚠️ **Missing Input Validation**: Services accept raw strings without validation
3. ⚠️ **No Caching Layer**: Global context queried on every request
4. ⚠️ **No Database Migrations**: `migrate_db.py` drops all data, no Alembic
5. ⚠️ **No API Documentation**: FastAPI docs not customized with descriptions

**LOW Priority Issues**:
6. ⚠️ **SQLite Not Production-Ready**: Single-file DB doesn't scale
7. ⚠️ **No Background Job Monitoring**: Scheduler crashes go unnoticed
8. ⚠️ **No Rate Limiting**: API can be abused with unlimited requests

**Architecture Score**: 8.5/10
- **Strengths**: Clean 3-layer architecture, complete repository adoption, error handling with fallback, retry logic, centralized config, health monitoring
- **Weaknesses**: No input validation, no caching, missing DB migrations, no API docs
- **Progress**: 7.5 → 8.0 (Phase 1) → 8.5 (Phase 2)

## Architecture Recommendations

**Completed** (2025-10-01):
1. ✅ Fix database session management (proper session-per-request pattern)
2. ✅ Split into Repository + Service + Router layers (Clean Architecture)
3. ✅ Add task ID system with autoincrement
4. ✅ Add comprehensive test coverage (21 unit tests + E2E tests)
5. ✅ Add toast notifications for user feedback
6. ✅ Migrate `schedule_checker.py` to use repositories (complete repository adoption)
7. ✅ Install Playwright in Docker (already in Dockerfile)
8. ✅ Add basic error handling to services (try-catch with fallback scheduling)
9. ✅ Create `config.py` with Pydantic Settings for centralized configuration
10. ✅ Add retry logic for DSPy calls (tenacity with exponential backoff)
11. ✅ Add `/health` endpoint to monitor app and DSPy API

**Phase 1: Fix Critical Issues** - MOSTLY COMPLETE:
1. ⚠️ Delete `app_new.py` duplicate file (requires manual deletion, rm command blocked)

**Phase 2: Production Readiness** - COMPLETE ✅

**Phase 3: Robustness** (3-5 hours):
8. Add input validation with Pydantic models
9. Implement Alembic for database migrations (no more data drops)
10. Add background job monitoring (APScheduler event listeners)
11. Add rate limiting (slowapi)

**Phase 4: Scaling** (ongoing):
12. Migrate to PostgreSQL with connection pooling
13. Add Redis caching for global context and DSPy results
14. Add comprehensive API documentation (OpenAPI metadata)

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

**Unit Test Coverage** (24 tests in test_app.py):
- Page rendering tests (index, calendar, tasks)
- Task lifecycle tests (create, start, complete, delete)
- Global context management
- DSPy execution logging
- Timezone consistency across models
- **ID autoincrement tests** (Task, GlobalContext, DSPyExecution)
- **ScheduledTask serialization** (id field inclusion)
- **Task-to-ScheduledTask conversion** (ID preservation)
- **Rescheduling logic** (existing_schedule excludes current task)
- **End-to-end ID flow** (DB → ScheduledTask → dict)

**E2E Test Coverage** (test_e2e.py with Playwright):
- Task operations: add, start, complete, delete with toast notifications
- Navigation: task list ↔ timeline, page switching
- Global context: update and persistence
- Active task tracker: appears on start, disappears on complete
- **Timeline view** (6 new tests):
  - Timeline page loads correctly
  - Scheduled tasks display in timeline
  - Multiple tasks appear simultaneously
  - Task times shown correctly
  - Empty state handling
  - Completed tasks styled differently
  - Chronological ordering verified

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

### Adding a New Task
1. User submits title + optional task-specific context via form
2. `TimeSlotModule` receives: new task, task context, **global context**, current datetime, existing schedule (with task IDs)
3. DeepSeek V3.2-Exp generates `scheduled_start_time` and `scheduled_end_time` with reasoning
4. Task saved to database with auto-incremented ID and scheduled times
5. `dspy_tracker` logs complete inference process to `DSPyExecution` table (including task IDs in schedule)
6. Logs show: inputs, outputs, duration, and reasoning

### Task Lifecycle States
- **Created**: Has scheduled times, no actual times
- **Started**: User clicked "Start", `actual_start_time` set
- **Completed**: User clicked "Complete", `actual_end_time` set

### Background Schedule Checking & Automatic Rescheduling
Every 5 seconds, `check_and_update_schedule()` runs in background thread:
1. Creates own database session (`SessionLocal()`)
2. Queries incomplete tasks
3. Checks if end time passed or start time passed (not started)
4. Calls `reschedule_task(db, task, now)` which:
   - Queries existing schedule (excluding current task)
   - Gets global context
   - Calls DSPy `TimeSlotModule` for new times
   - **`db.refresh(task)`** before updating (prevents `StaleDataError`)
   - Commits new scheduled times
5. Closes session in `finally` block
6. Logs: "🔄 Rescheduled {n} task(s)" with new times

## Environment Configuration

Required in `.env`:
- `OPENROUTER_API_KEY`: API key for OpenRouter (DeepSeek access)
- `DATABASE_URL`: SQLite database path (default: `sqlite:///tasks.db`)

Current LM configuration in `app.py`:
```python
lm = dspy.LM('openrouter/deepseek/deepseek-v3.2-exp', api_key=os.getenv('OPENROUTER_API_KEY'))
```

## Testing

### Running Tests
```bash
docker compose exec web pytest test_app.py -v
```

### Test Coverage (21 tests)
- HTTP endpoints (routes, services, repositories working together)
- Task CRUD operations
- Global context management
- Inference log retrieval
- Timezone consistency across all models
- ID autoincrement for all models
- ScheduledTask serialization with IDs
- End-to-end ID flow from DB → ScheduledTask → dict

### Test Database
- Uses separate `test_tasks.db`
- Each test creates fresh session with `SessionLocal()`
- Cleanup in fixture ensures test isolation

## Database Schema Changes

When modifying models in `models.py`:
1. Update the model class
2. Run `docker compose exec web python migrate_db.py` (WARNING: drops all data)
3. Restart container with `docker compose restart web`
4. Verify no errors in logs

## Context System

### Global Context
User-wide preferences and constraints stored in `GlobalContext` table. Accessed via dedicated UI. Examples:
- Work hours: "I work 9am-5pm Monday-Friday"
- Preferences: "I prefer deep work in mornings, meetings in afternoons"
- Constraints: "No tasks after 6pm or on weekends"

### Task Context
Task-specific context stored in `Task.context` field. Examples:
- Priorities: "urgent", "low priority"
- Constraints: "must be after lunch", "before 5pm"
- Requirements: "need 2 hour blocks", "prefer mornings"

Both contexts are passed to DSPy modules for scheduling and prioritization decisions. All context is logged during inference for debugging.

## UI Design

**Theme**: Monochrome black and white with glassmorphism effects
- **Background**: Radial gradient from dark gray to black
- **Components**: Translucent glass cards with backdrop-filter blur
- **Animations**: Fade-in, hover lifts, button scales, smooth transitions
- **Typography**: System font stack, clear hierarchy
- **Layout**: Card-based sections with proper spacing
- **Active Task Tracker**: Fixed top-right with pulse animation
- **Toast Notifications**: Bottom-right with glassmorphism, auto-dismiss after 2s

**Toast System** (`base.html`):
- Global `showToast(message, duration)` function
- Fixed position bottom-right (z-index: 2000)
- Green glassmorphism styling with backdrop blur
- Slide-up animation on appear, fade-out on dismiss
- Triggered via HTMX `hx-on::after-request` on all task operations

All styles centralized in `base.html` for consistency.

## Recent Changes

### 2025-10-01: Critical Database Session Fix & Architecture Refactoring
**Fixed critical data loss bug and implemented clean architecture:**

1. **Database Session Management Fix** (CRITICAL):
   - **Problem**: Tasks disappearing due to `PendingRollbackError`
   - **Root Cause**: Global `db` session shared across requests and background jobs
   - **Solution**: Session-per-request pattern
     - Routes: `db: Session = Depends(get_db)`
     - Background jobs: `SessionLocal()` in try/finally
     - DSPy tracker: Own session for thread safety
   - **Files**: `models.py`, `app.py`, `schedule_checker.py`, `dspy_tracker.py`, `test_app.py`
   - **Result**: No more data loss

2. **Repository + Service Layer Implementation**:
   - Refactored `app.py` (171 lines → 54 lines, 68% reduction)
   - Three-layer architecture:
     - Repositories: Data access (`task_repository.py`, etc.)
     - Services: Business logic (`task_service.py`, etc.)
     - Routers: HTTP layer (`task_router.py`, etc.)
   - Fixed circular imports using `get_time_scheduler()` getter

3. **DSPy Input Logging Fix**:
   - **Problem**: Execution logs showed empty inputs `📥 INPUT - {}`
   - **Root Cause**: Decorator captured empty lambda kwargs
   - **Solution**: Refactored `track_dspy_execution()` to accept params directly
   - **Files**: `dspy_tracker.py`, `scheduler.py`
   - **Result**: Full visibility into DSPy inputs/outputs

4. **Timezone Consistency**:
   - Changed all datetime from `datetime.utcnow` to `datetime.now`
   - Applied to: `Task.created_at`, `GlobalContext.updated_at`, `DSPyExecution.created_at`
   - Added 3 timezone consistency tests
   - **Files**: `models.py`, `test_app.py`

5. **UX Improvements**:
   - Enter key submission for task title field
   - Inference log inverted (newest at bottom with auto-scroll)
   - **Files**: `templates/index.html`, `templates/inference_log.html`

6. **Test Coverage**: Updated all 12 tests + added 9 new tests (21 total) ✅

### 2025-10-01: Toast Notification System
**Added user feedback for all database operations:**

1. **Toast Notification System**:
   - Global JavaScript function `showToast(message, duration)` in `base.html`
   - Fixed bottom-right position with glassmorphism styling
   - Auto-dismiss after 2 seconds with fade-out animation
   - Consistent with app's black/white/green design theme

2. **Integrated with All Task Operations**:
   - ✓ Task added
   - ✓ Task started
   - ✓ Task completed
   - ✓ Task deleted
   - Triggered via HTMX `hx-on::after-request` attribute

**Files Modified**:
- `base.html`: Added toast container, styles, and JavaScript function
- `index.html`: Added toast trigger to task form
- `task_item.html`: Added toast triggers to start/complete/delete buttons

**Benefits**:
- Immediate visual feedback for user actions
- Better UX - users know operations succeeded
- Consistent notification system across all operations

### 2025-10-01: Router-Based Architecture & ID System
**Major refactoring to improve code organization and enable task referencing:**

1. **Router-Based Architecture**:
   - Split monolithic `app.py` (171 lines) into modular structure (~53 lines)
   - Created `routers/` directory: `task_router.py`, `context_router.py`, `inference_router.py`
   - Improved separation of concerns, easier maintenance and testing

2. **Task ID System**:
   - Added explicit `autoincrement=True` to all model primary keys
   - Updated `ScheduledTask` Pydantic model to include `id` field
   - Modified all Task→ScheduledTask conversions to preserve IDs
   - Enables DSPy modules to reference specific tasks in scheduling decisions

3. **Comprehensive Test Coverage**:
   - Added 8 new tests for ID functionality (21 total tests)
   - Tests cover: autoincrement, serialization, conversion, exclusion logic, end-to-end flow
   - All tests passing ✓

**Files Modified**:
- `app.py`: Reduced to ~53 lines, now only handles app initialization
- `models.py`: Added autoincrement to all IDs
- `scheduler.py`: Added id field to ScheduledTask
- `schedule_checker.py`: Include task IDs in ScheduledTask creation
- `test_app.py`: Added comprehensive ID system tests
- Created `routers/task_router.py`, `routers/context_router.py`, `routers/inference_router.py`

**Benefits**:
- Cleaner code organization with router-based structure
- DSPy can reference tasks by ID for intelligent scheduling
- Better test coverage for critical functionality
- Easier to add new routes and features
