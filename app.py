from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import dspy
from models import init_db
from scheduler import PrioritizerModule, TimeSlotModule
import schedule_checker
from schedule_checker import ScheduleChecker
from config import settings
from datetime import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from routers import task_router, context_router, inference_router, settings_router, chat_router

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

# Initialize database
init_db()

# Initialize DSPy
lm = dspy.LM(settings.dspy_model, api_key=settings.openrouter_api_key)
dspy.configure(lm=lm)
prioritizer = PrioritizerModule()
time_scheduler = TimeSlotModule()

# Global scheduler reference
bg_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global bg_scheduler

    # Startup
    logger.info("Starting application...")

    # Store schedule checker in app state for dependency injection
    schedule_checker_instance = ScheduleChecker(time_scheduler)
    app.state.schedule_checker = schedule_checker_instance

    if settings.scheduler_enabled:
        bg_scheduler = BackgroundScheduler()
        bg_scheduler.add_job(schedule_checker_instance.check_and_update_schedule, 'interval', seconds=settings.scheduler_interval_seconds)
        bg_scheduler.start()
        logger.info(f"Background scheduler started (interval: {settings.scheduler_interval_seconds}s)")
    else:
        logger.info("Background scheduler disabled")

    yield

    # Shutdown
    if bg_scheduler is not None:
        logger.info("Shutting down background scheduler...")
        bg_scheduler.shutdown()
        logger.info("Background scheduler shut down successfully")

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)


def get_schedule_checker(request: Request) -> ScheduleChecker:
    """Dependency to get schedule checker from app state"""
    if not hasattr(request.app.state, 'schedule_checker'):
        # For tests or when scheduler not initialized
        return ScheduleChecker(time_scheduler)
    return request.app.state.schedule_checker


# Include routers
app.include_router(task_router.router)
app.include_router(context_router.router)
app.include_router(inference_router.router)
app.include_router(settings_router.router)
app.include_router(chat_router.router)


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, 'index.html')


@app.get('/health')
async def health_check():
    """Health check endpoint for monitoring"""
    from models import SessionLocal

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Check database connectivity
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    finally:
        db.close()

    # Check DSPy availability
    try:
        if time_scheduler is not None:
            health_status["components"]["dspy_scheduler"] = "initialized"
        else:
            health_status["components"]["dspy_scheduler"] = "not_initialized"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["dspy_scheduler"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check background scheduler
    try:
        if settings.scheduler_enabled:
            if bg_scheduler is not None and bg_scheduler.running:
                health_status["components"]["background_scheduler"] = "running"
            else:
                health_status["components"]["background_scheduler"] = "enabled_but_not_running"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["background_scheduler"] = "disabled"
    except Exception as e:
        health_status["components"]["background_scheduler"] = f"error: {str(e)}"

    return health_status


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
