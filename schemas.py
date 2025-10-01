from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", max_length=1000, description="Task description")
    context: str = Field(default="", max_length=1000, description="Task-specific context for scheduling")
    due_date: Optional[str] = Field(default=None, description="Due date in ISO format")

    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()

    @validator('description')
    def description_max_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Description cannot exceed 1000 characters')
        return v

    @validator('context')
    def context_max_length(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Context cannot exceed 1000 characters')
        return v


class ContextUpdate(BaseModel):
    """Schema for updating global context"""
    context: str = Field(..., max_length=5000, description="Global context about priorities and constraints")

    @validator('context')
    def context_max_length(cls, v):
        if v and len(v) > 5000:
            raise ValueError('Global context cannot exceed 5000 characters')
        return v
