from sqlalchemy.orm import Session
from models import ChatMessage
from typing import List
import logging

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository for ChatMessage database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, chat_message: ChatMessage) -> ChatMessage:
        """Create a new chat message"""
        self.db.add(chat_message)
        self.db.commit()
        self.db.refresh(chat_message)
        logger.info(f"Created chat message ID={chat_message.id}")
        return chat_message

    def get_recent(self, limit: int = 50) -> List[ChatMessage]:
        """Get recent chat messages ordered by creation time desc"""
        return self.db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()

    def get_all(self) -> List[ChatMessage]:
        """Get all chat messages ordered by creation time"""
        return self.db.query(ChatMessage).order_by(ChatMessage.created_at).all()

    def delete_all(self) -> int:
        """Delete all chat messages and return count"""
        count = self.db.query(ChatMessage).count()
        self.db.query(ChatMessage).delete()
        self.db.commit()
        logger.info(f"Deleted all chat messages (count={count})")
        return count
