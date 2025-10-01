from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.context_repository import GlobalContextRepository
from services.context_service import ContextService
from schemas import ContextUpdate
from pydantic import ValidationError

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_context_service(db: Session = Depends(get_db)):
    """Dependency to get context service"""
    context_repo = GlobalContextRepository(db)
    return ContextService(context_repo)


@router.get('/global-context', response_class=HTMLResponse)
async def get_context(request: Request, service: ContextService = Depends(get_context_service)):
    context = service.get_context()
    return templates.TemplateResponse('global_context.html', {'request': request, 'context': context})


@router.post('/global-context', response_class=HTMLResponse)
async def update_context(request: Request, context: str = Form(...), service: ContextService = Depends(get_context_service)):
    # Validate input using Pydantic schema
    try:
        context_data = ContextUpdate(context=context)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    context_text = service.update_context(context_data.context)
    return templates.TemplateResponse('global_context.html', {'request': request, 'context': context_text})
