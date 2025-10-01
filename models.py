from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, default='')
    context = Column(String, default='')
    due_date = Column(DateTime, nullable=True)
    scheduled_start_time = Column(DateTime, nullable=True)
    scheduled_end_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    priority = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class GlobalContext(Base):
    __tablename__ = 'global_context'

    id = Column(Integer, primary_key=True, autoincrement=True)
    context = Column(Text, default='')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class DSPyExecution(Base):
    __tablename__ = 'dspy_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_name = Column(String, nullable=False)
    inputs = Column(Text, nullable=False)
    outputs = Column(Text, nullable=False)
    duration_ms = Column(Float, nullable=False)
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
