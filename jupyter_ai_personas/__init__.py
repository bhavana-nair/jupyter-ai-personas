def hello() -> str:
    return "Hello from jupyter-ai-personas!"

# Export personas
from .task_master.persona_task_master import PRReviewPersonaTaskMaster

__all__ = ['PRReviewPersonaTaskMaster']
