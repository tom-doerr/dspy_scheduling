from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.chat_repository import ChatRepository
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from services.chat_service import ChatService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_chat_service(db: Session = Depends(get_db)):
    """Dependency to get chat service"""
    chat_repo = ChatRepository(db)
    task_repo = TaskRepository(db)
    context_repo = GlobalContextRepository(db)
    return ChatService(chat_repo, task_repo, context_repo)


@router.get('/chat', response_class=HTMLResponse)
async def chat_page(request: Request, service: ChatService = Depends(get_chat_service)):
    messages = service.get_chat_history(limit=50)
    return templates.TemplateResponse(request, 'chat.html', {'messages': list(reversed(messages))})


@router.post('/chat/send', response_class=HTMLResponse)
async def send_message(
    request: Request,
    message: str = Form(...),
    service: ChatService = Depends(get_chat_service)
):
    chat_message = service.process_message(message)
    return templates.TemplateResponse(request, 'chat_message.html', {'msg': chat_message})


@router.post('/chat/clear', response_class=HTMLResponse)
async def clear_chat(request: Request, service: ChatService = Depends(get_chat_service)):
    count = service.clear_chat_history()
    return templates.TemplateResponse(request, 'chat_history.html', {'messages': []})
