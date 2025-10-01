from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from models import get_db
from sqlalchemy.orm import Session
from repositories.dspy_execution_repository import DSPyExecutionRepository
from services.inference_service import InferenceService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_inference_service(db: Session = Depends(get_db)):
    """Dependency to get inference service"""
    execution_repo = DSPyExecutionRepository(db)
    return InferenceService(execution_repo)


@router.get('/inference-log', response_class=HTMLResponse)
async def get_inference_log(request: Request, service: InferenceService = Depends(get_inference_service)):
    executions = service.get_latest_executions()
    return templates.TemplateResponse(request, 'inference_log.html', {'executions': executions})
