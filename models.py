from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (
        Index('ix_tasks_completed', 'completed'),
        Index('ix_tasks_scheduled_start', 'scheduled_start_time'),
        Index('ix_tasks_needs_scheduling', 'needs_scheduling'),
        Index('ix_tasks_actual_start', 'actual_start_time'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), default='')
    context = Column(String(1000), default='')
    due_date = Column(DateTime, nullable=True)
    scheduled_start_time = Column(DateTime, nullable=True)
    scheduled_end_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    priority = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    needs_scheduling = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class GlobalContext(Base):
    __tablename__ = 'global_context'

    id = Column(Integer, primary_key=True, autoincrement=True)
    singleton = Column(Boolean, default=True, unique=True, nullable=False)
    context = Column(Text, default='')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class DSPyExecution(Base):
    __tablename__ = 'dspy_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_name = Column(String(100), nullable=False)
    inputs = Column(Text, nullable=False)
    outputs = Column(Text, nullable=False)
    duration_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    singleton = Column(Boolean, default=True, unique=True, nullable=False)
    llm_model = Column(String(200), default='openrouter/deepseek/deepseek-v3.2-exp', nullable=False)
    max_tokens = Column(Integer, default=2000, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

from config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """Get database session - use this instead of global db"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(engine)
