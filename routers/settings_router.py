from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.settings_repository import SettingsRepository
from services.settings_service import SettingsService
from schemas import SettingsUpdate
from pydantic import ValidationError

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_settings_service(db: Session = Depends(get_db)):
    """Dependency to get settings service"""
    settings_repo = SettingsRepository(db)
    return SettingsService(settings_repo)


@router.get('/settings', response_class=HTMLResponse)
async def settings_page(request: Request, service: SettingsService = Depends(get_settings_service)):
    settings = service.get_settings()
    return templates.TemplateResponse(request, 'settings.html', {'settings': settings})


@router.get('/settings-form', response_class=HTMLResponse)
async def settings_form(request: Request, service: SettingsService = Depends(get_settings_service)):
    settings = service.get_settings()
    return templates.TemplateResponse(request, 'settings_form.html', {'settings': settings})


@router.post('/settings', response_class=HTMLResponse)
async def update_settings(
    request: Request,
    llm_model: str = Form(...),
    max_tokens: int = Form(...),
    service: SettingsService = Depends(get_settings_service)
):
    # Validate input using Pydantic schema
    try:
        settings_data = SettingsUpdate(llm_model=llm_model, max_tokens=max_tokens)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        settings = service.update_settings(settings_data.llm_model, settings_data.max_tokens)
        return templates.TemplateResponse(request, 'settings_form.html', {'settings': settings})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
