from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from services.task_service import TaskService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_task_service(db: Session = Depends(get_db)):
    """Dependency to get task service"""
    # Get time_scheduler from schedule_checker to avoid circular import
    from schedule_checker import get_time_scheduler
    time_scheduler = get_time_scheduler()
    task_repo = TaskRepository(db)
    context_repo = GlobalContextRepository(db)
    return TaskService(task_repo, context_repo, time_scheduler)


@router.get('/tasks', response_class=HTMLResponse)
async def get_tasks(request: Request, service: TaskService = Depends(get_task_service)):
    tasks = service.get_all_tasks()
    return templates.TemplateResponse('tasks.html', {'request': request, 'tasks': tasks})


@router.get('/calendar', response_class=HTMLResponse)
async def calendar_view(request: Request, service: TaskService = Depends(get_task_service)):
    tasks = service.get_scheduled_tasks()
    return templates.TemplateResponse('calendar.html', {'request': request, 'tasks': tasks})


@router.get('/active-task', response_class=HTMLResponse)
async def get_active_task(request: Request, service: TaskService = Depends(get_task_service)):
    task = service.get_active_task()
    return templates.TemplateResponse('active_task.html', {'request': request, 'task': task})


@router.post('/tasks', response_class=HTMLResponse)
async def add_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    context: str = Form(""),
    due_date: str = Form(None),
    service: TaskService = Depends(get_task_service)
):
    task = service.create_task(title, description, context, due_date)
    return templates.TemplateResponse('task_item.html', {'request': request, 'task': task})


@router.post('/tasks/{task_id}/start', response_class=HTMLResponse)
async def start_task(request: Request, task_id: int, service: TaskService = Depends(get_task_service)):
    task = service.start_task(task_id)
    return templates.TemplateResponse('task_item.html', {'request': request, 'task': task})


@router.post('/tasks/{task_id}/complete', response_class=HTMLResponse)
async def complete_task(request: Request, task_id: int, service: TaskService = Depends(get_task_service)):
    task = service.complete_task(task_id)
    return templates.TemplateResponse('task_item.html', {'request': request, 'task': task})


@router.delete('/tasks/{task_id}')
async def delete_task(task_id: int, service: TaskService = Depends(get_task_service)):
    service.delete_task(task_id)
    return ''
