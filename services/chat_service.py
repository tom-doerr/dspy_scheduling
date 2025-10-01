"""Chat service for natural language task management"""

import json
import logging
from typing import Dict, Any
from models import ChatMessage
from repositories.chat_repository import ChatRepository
from repositories.task_repository import TaskRepository
from repositories.context_repository import GlobalContextRepository
from chat_assistant import ChatAssistantModule
from dspy_tracker import track_dspy_execution


logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat assistant with task management capabilities"""

    def __init__(
        self,
        chat_repo: ChatRepository,
        task_repo: TaskRepository,
        context_repo: GlobalContextRepository
    ):
        self.chat_repo = chat_repo
        self.task_repo = task_repo
        self.context_repo = context_repo
        self.assistant = ChatAssistantModule()

    def _get_task_list_json(self) -> str:
        """Get current tasks as JSON"""
        tasks = self.task_repo.get_all()
        task_data = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "context": t.context,
                "priority": t.priority,
                "completed": t.completed,
                "scheduled_start": str(t.scheduled_start_time) if t.scheduled_start_time else None,
                "scheduled_end": str(t.scheduled_end_time) if t.scheduled_end_time else None,
                "actual_start": str(t.actual_start_time) if t.actual_start_time else None
            }
            for t in tasks
        ]
        return json.dumps(task_data)

    def _execute_action(self, action: str, task_id: int, title: str, description: str, context: str) -> Dict[str, Any]:
        """Execute the specified action and return result"""
        from models import Task

        if action == "create_task":
            task = Task(
                title=title or "Untitled Task",
                description=description or "",
                context=context or "",
                needs_scheduling=True
            )
            created = self.task_repo.create(task)
            return {"success": True, "task_id": created.id, "message": f"Task '{created.title}' created"}

        elif action == "start_task" and task_id:
            task = self.task_repo.get_by_id(task_id)
            if task is None:
                logger.warning(f"Cannot start task: Task ID={task_id} not found")
                return {"success": False, "message": "Task not found"}
            self.task_repo.start_task(task)
            return {"success": True, "message": f"Task '{task.title}' started"}

        elif action == "complete_task" and task_id:
            task = self.task_repo.get_by_id(task_id)
            if task is None:
                logger.warning(f"Cannot complete task: Task ID={task_id} not found")
                return {"success": False, "message": "Task not found"}
            self.task_repo.complete_task(task)
            return {"success": True, "message": f"Task '{task.title}' completed"}

        elif action == "stop_task" and task_id:
            task = self.task_repo.get_by_id(task_id)
            if task is None:
                logger.warning(f"Cannot stop task: Task ID={task_id} not found")
                return {"success": False, "message": "Task not found"}
            self.task_repo.stop_task(task)
            return {"success": True, "message": f"Task '{task.title}' stopped"}

        elif action == "delete_task" and task_id:
            task = self.task_repo.get_by_id(task_id)
            if task is None:
                logger.warning(f"Cannot delete task: Task ID={task_id} not found")
                return {"success": False, "message": "Task not found"}
            title_backup = task.title
            self.task_repo.delete(task)
            return {"success": True, "message": f"Task '{title_backup}' deleted"}

        return {"success": True, "message": "Action executed"}

    @track_dspy_execution("ChatAssistantModule")
    def process_message(self, user_message: str) -> ChatMessage:
        """Process user message, execute actions, and return chat response"""
        # Get current task list and global context
        task_list = self._get_task_list_json()
        global_context = self.context_repo.get_or_create().context or "No global context set"

        # Call DSPy assistant
        result = self.assistant.forward(
            user_message=user_message,
            task_list=task_list,
            global_context=global_context
        )

        # Execute action if specified
        action_result = None
        if result.action and result.action != "chat" and result.action != "list_tasks":
            try:
                action_result = self._execute_action(
                    action=result.action,
                    task_id=result.task_id,
                    title=result.title,
                    description=result.description,
                    context=result.context
                )
                logger.info(f"Action '{result.action}' executed: {action_result}")
            except Exception as e:
                logger.error(f"Error executing action '{result.action}': {e}")
                action_result = {"success": False, "message": str(e)}

        # Prepare final response
        final_response = result.response
        if action_result and not action_result.get("success"):
            final_response += f"\n\nNote: {action_result['message']}"

        # Store chat message
        chat_message = ChatMessage(
            user_message=user_message,
            assistant_response=final_response
        )
        return self.chat_repo.create(chat_message)

    def get_chat_history(self, limit: int = 50):
        """Get recent chat history"""
        return self.chat_repo.get_recent(limit=limit)

    def clear_chat_history(self) -> int:
        """Clear all chat history and return count"""
        return self.chat_repo.delete_all()
