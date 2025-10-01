"""DSPy-based chat assistant with tool calling for task management"""

import dspy
from typing import Optional
from pydantic import BaseModel, Field


class TaskAction(BaseModel):
    """Structured output for task actions"""
    action: str = Field(description="Action type: create_task, update_task, delete_task, start_task, complete_task, stop_task, list_tasks, get_task")
    task_id: Optional[int] = Field(default=None, description="Task ID for update/delete/start/complete/stop operations")
    title: Optional[str] = Field(default=None, description="Task title for create/update")
    description: Optional[str] = Field(default=None, description="Task description")
    context: Optional[str] = Field(default=None, description="Task context (priority, constraints)")
    response: str = Field(description="Natural language response to user")


class ChatSignature(dspy.Signature):
    """Signature for chat assistant with task management capabilities"""
    user_message: str = dspy.InputField(desc="User's message/question/command")
    task_list: str = dspy.InputField(desc="Current tasks in JSON format")
    global_context: str = dspy.InputField(desc="User's global context and preferences")

    action: str = dspy.OutputField(desc="Action type")
    task_id: Optional[int] = dspy.OutputField(desc="Task ID for operations")
    title: Optional[str] = dspy.OutputField(desc="Task title")
    description: Optional[str] = dspy.OutputField(desc="Task description")
    context: Optional[str] = dspy.OutputField(desc="Task context")
    response: str = dspy.OutputField(desc="Natural language response")


class ChatAssistantModule(dspy.Module):
    """Chat assistant that can manage tasks through natural language"""

    def __init__(self):
        super().__init__()
        self.assistant = dspy.ChainOfThought(ChatSignature)

    def forward(self, user_message: str, task_list: str, global_context: str):
        """Process user message and return action + response"""
        result = self.assistant(
            user_message=user_message,
            task_list=task_list,
            global_context=global_context
        )

        return dspy.Prediction(
            action=result.action,
            task_id=result.task_id,
            title=result.title,
            description=result.description,
            context=result.context,
            response=result.response
        )
