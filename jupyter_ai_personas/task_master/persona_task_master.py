from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from langchain_core.messages import HumanMessage
from .pr_task_master import PRTaskMaster
from ..pr_review_persona.template import PRPersonaVariables, PR_PROMPT_TEMPLATE

class PRReviewPersonaTaskMaster(BasePersona):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_master = None
    
    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRReviewPersona_TaskMaster",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="Task-orchestrated PR review assistant with intelligent workflow management.",
            system_prompt="Advanced PR reviewer using task orchestration for comprehensive analysis.",
        )
    
    def _initialize_task_master(self):
        if not self.task_master:
            self.task_master = PRTaskMaster()
        return self.task_master
    
    async def process_message(self, message: Message):
        try:
            # Get chat history
            history = YChatHistory(ychat=self.ychat, k=2)
            messages = await history.aget_messages()
            
            history_text = ""
            if messages:
                history_text = "\nPrevious conversation:\n"
                for msg in messages:
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    history_text += f"{role}: {msg.content}\n"
            
            # Prepare context
            variables = PRPersonaVariables(
                input=message.body,
                model_id="gemini-2.5-pro",
                provider_name="google",
                persona_name=self.name,
                context=history_text
            )
            
            # Initialize task master
            task_master = self._initialize_task_master()
            
            # Execute PR review workflow
            review_results = await task_master.review_pr(message.body)
            
            # Format response
            response = self._format_response(review_results)
            
            self.send_message(response)
            
        except Exception as e:
            error_msg = f"Task orchestration failed: {str(e)}"
            self.send_message(error_msg)
    
    def _format_response(self, results: dict) -> str:
        response_parts = [
            "# PR Review Results (Task Master)",
            "",
            f"**Summary:** {results['summary']}",
            ""
        ]
        
        # Task status overview
        response_parts.append("## Task Execution Status")
        for task_id, status in results['status'].items():
            emoji = "✅" if status.value == "completed" else "❌" if status.value == "failed" else "⏳"
            response_parts.append(f"- {emoji} {task_id}: {status.value}")
        
        response_parts.append("")
        
        # Detailed results
        response_parts.append("## Analysis Results")
        if results['results']:
            for task_id, result in results['results'].items():
                response_parts.append(f"### {task_id}")
                if result:
                    result_str = str(result)
                    if len(result_str) > 500:
                        response_parts.append(result_str[:500] + "...")
                    else:
                        response_parts.append(result_str)
                else:
                    response_parts.append("*No result returned*")
                response_parts.append("")
        else:
            response_parts.append("*No results available*")
            
        # Add debug info
        response_parts.append("## Debug Info")
        response_parts.append(f"Total tasks: {len(results.get('status', {}))}")
        response_parts.append(f"Results keys: {list(results.get('results', {}).keys())}")
        
        return "\n".join(response_parts)