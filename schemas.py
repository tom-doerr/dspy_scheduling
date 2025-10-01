from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", max_length=1000, description="Task description")
    context: str = Field(default="", max_length=1000, description="Task-specific context for scheduling")
    due_date: Optional[str] = Field(default=None, description="Due date in ISO format")

    @field_validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()

    @field_validator('description')
    def description_max_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Description cannot exceed 1000 characters')
        return v

    @field_validator('context')
    def context_max_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Context cannot exceed 1000 characters')
        return v


class ContextUpdate(BaseModel):
    """Schema for updating global context"""
    context: str = Field(..., max_length=5000, description="Global context about priorities and constraints")

    @field_validator('context')
    def context_max_length(cls, v):
        if v and len(v) > 5000:
            raise ValueError('Global context cannot exceed 5000 characters')
        return v


class SettingsUpdate(BaseModel):
    """Schema for updating settings"""
    llm_model: str = Field(..., min_length=1, max_length=200, description="LLM model name (e.g., openrouter/deepseek/deepseek-v3.2-exp)")
    max_tokens: int = Field(..., ge=100, le=10000, description="Maximum tokens for LLM responses")

    @field_validator('llm_model')
    def validate_llm_model(cls, v):
        if not v or not v.strip():
            raise ValueError('LLM model name cannot be empty')
        # Basic format check for provider/model pattern
        if '/' not in v:
            raise ValueError('LLM model must include provider (e.g., openrouter/deepseek/model-name)')
        return v.strip()

    @field_validator('max_tokens')
    def validate_max_tokens(cls, v):
        if v < 100 or v > 10000:
            raise ValueError('max_tokens must be between 100 and 10000')
        return v
