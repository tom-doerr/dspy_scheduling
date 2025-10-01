from fastapi import APIRouter, Request, Form, Depends, HTTPException, Path
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from services.task_service import TaskService
from schemas import TaskCreate
from pydantic import ValidationError

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
    return templates.TemplateResponse(request, 'tasks.html', {'tasks': tasks})


@router.get('/calendar', response_class=HTMLResponse)
async def calendar_view(request: Request, service: TaskService = Depends(get_task_service)):
    tasks = service.get_scheduled_tasks()
    return templates.TemplateResponse(request, 'calendar.html', {'tasks': tasks})


@router.get('/history', response_class=HTMLResponse)
async def history_view(request: Request, service: TaskService = Depends(get_task_service)):
    tasks = service.get_completed_tasks()
    return templates.TemplateResponse(request, 'history.html', {'tasks': tasks})


@router.get('/active-task', response_class=HTMLResponse)
async def get_active_task(request: Request, service: TaskService = Depends(get_task_service)):
    task = service.get_active_task()
    return templates.TemplateResponse(request, 'active_task.html', {'task': task})


@router.post('/tasks', response_class=HTMLResponse)
async def add_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    context: str = Form(""),
    due_date: str = Form(None),
    service: TaskService = Depends(get_task_service)
):
    # Validate input using Pydantic schema
    try:
        task_data = TaskCreate(title=title, description=description, context=context, due_date=due_date)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    task = service.create_task(task_data.title, task_data.description, task_data.context, task_data.due_date)
    return templates.TemplateResponse(request, 'task_item.html', {'task': task})


@router.post('/tasks/{task_id}/start', response_class=HTMLResponse)
async def start_task(request: Request, task_id: int = Path(..., gt=0), service: TaskService = Depends(get_task_service)):
    try:
        task = service.start_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return templates.TemplateResponse(request, 'task_item.html', {'task': task})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/tasks/{task_id}/stop', response_class=HTMLResponse)
async def stop_task(request: Request, task_id: int = Path(..., gt=0), service: TaskService = Depends(get_task_service)):
    try:
        task = service.stop_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return templates.TemplateResponse(request, 'task_item.html', {'task': task})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/tasks/{task_id}/complete', response_class=HTMLResponse)
async def complete_task(request: Request, task_id: int = Path(..., gt=0), service: TaskService = Depends(get_task_service)):
    try:
        task = service.complete_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return templates.TemplateResponse(request, 'task_item.html', {'task': task})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete('/tasks/{task_id}')
async def delete_task(task_id: int = Path(..., gt=0), service: TaskService = Depends(get_task_service)):
    service.delete_task(task_id)
    return ''
