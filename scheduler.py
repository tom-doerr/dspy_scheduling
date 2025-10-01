import dspy
from typing import List
from pydantic import BaseModel, Field

class TaskInput(BaseModel):
    id: int
    title: str
    description: str = ""
    due_date: str | None = None

class PrioritizedTask(BaseModel):
    id: int
    title: str
    priority: float = Field(ge=0, le=10, description="Priority score from 0 to 10")
    reasoning: str = Field(description="Explanation for the priority")

class ScheduledTask(BaseModel):
    id: int
    title: str
    start_time: str = Field(description="ISO format datetime")
    end_time: str = Field(description="ISO format datetime")

class TaskPrioritizer(dspy.Signature):
    """Analyze tasks and prioritize them based on urgency, importance, and due dates."""

    tasks: List[TaskInput] = dspy.InputField(desc="List of tasks to prioritize")
    global_context: str = dspy.InputField(desc="Global context about user's priorities and constraints")
    prioritized_tasks: List[PrioritizedTask] = dspy.OutputField(desc="Tasks with priority scores and reasoning")

class TimeSlotScheduler(dspy.Signature):
    """Generate optimal start and end times for a new task based on existing schedule."""

    new_task: str = dspy.InputField(desc="New task title")
    task_context: str = dspy.InputField(desc="Task-specific context")
    global_context: str = dspy.InputField(desc="Global context about user's priorities and constraints")
    current_datetime: str = dspy.InputField(desc="Current date and time in ISO format")
    existing_schedule: List[ScheduledTask] = dspy.InputField(desc="Current scheduled tasks")
    start_time: str = dspy.OutputField(desc="Suggested start time in ISO format")
    end_time: str = dspy.OutputField(desc="Suggested end time in ISO format")
    reasoning: str = dspy.OutputField(desc="Explanation for the chosen time slot")

class PrioritizerModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.prioritize = dspy.ChainOfThought(TaskPrioritizer)

    def forward(self, tasks, global_context):
        from dspy_tracker import track_dspy_execution
        return track_dspy_execution("TaskPrioritizer", tasks=tasks, global_context=global_context)(
            lambda: self.prioritize(tasks=tasks, global_context=global_context)
        )

def _serialize_schedule(existing_schedule):
    """Serialize schedule for logging - converts ScheduledTask objects to dicts"""
    return [
        s.dict() if hasattr(s, 'dict') else {
            'id': s.id,
            'title': s.title,
            'start_time': s.start_time,
            'end_time': s.end_time
        }
        for s in existing_schedule
    ]

class TimeSlotModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.schedule_time = dspy.ChainOfThought(TimeSlotScheduler)

    def forward(self, new_task, task_context, global_context, current_datetime, existing_schedule):
        from dspy_tracker import track_dspy_execution
        serialized_schedule = _serialize_schedule(existing_schedule)
        return track_dspy_execution(
            "TimeSlotScheduler",
            new_task=new_task,
            task_context=task_context,
            global_context=global_context,
            current_datetime=current_datetime,
            existing_schedule=serialized_schedule
        )(
            lambda: self.schedule_time(
                new_task=new_task,
                task_context=task_context,
                global_context=global_context,
                current_datetime=current_datetime,
                existing_schedule=existing_schedule
            )
        )
