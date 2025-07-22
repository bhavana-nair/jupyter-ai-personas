from typing import Any

import emoji
from jupyterlab_chat.models import Message
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from agno.utils.log import logger

from jupyter_ai.history import YChatHistory
from jupyter_ai.personas import BasePersona, PersonaDefaults
from jupyter_ai.personas.jupyternaut.prompt_template import JupyternautVariables

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)


_SYSTEM_PROMPT_FORMAT = """
<instructions>

You are {{persona_name}}, an AI agent provided in JupyterLab through the 'Jupyter AI' extension.

Jupyter AI is an installable software package listed on PyPI and Conda Forge as `jupyter-ai`.

When installed, Jupyter AI adds a chat experience in JupyterLab that allows multiple users to collaborate with one or more agents like yourself.

You are not a language model, but rather an AI agent powered by a foundation model `{{model_id}}`, provided by '{{provider_name}}'.

You are receiving a request from a user in JupyterLab. Your goal is to respond to user's query with emojis (:emoji: format) in response.

You will receive any provided context and a relevant portion of the chat history.

The user's request is located at the last message. Please fulfill the user's request to the best of your ability.
</instructions>

<context>
{% if context %}The user has shared the following context:

{{context}}
{% else %}The user did not share any additional context.{% endif %}
</context>
""".strip()

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            _SYSTEM_PROMPT_FORMAT, template_format="jinja2"
        ),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

class EmojiPersona(BasePersona):
    """
    The Emoji persona, responds to your queries with emojis.
    
    Validates configuration and handles initialization errors appropriately.
    Sets up logging and manages resources safely.
    
    Args:
        *args: Arguments to pass to parent class
        **kwargs: Keyword arguments to pass to parent class
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
            
            # Validate required configuration
            if not self.config:
                raise ValueError("Configuration is required")
                
            if not hasattr(self.config, 'lm_provider'):
                raise ValueError("LM provider configuration is missing")
                
            if not hasattr(self.config.lm_provider, 'name') or not self.config.lm_provider.name:
                raise ValueError("LM provider name is missing")
                
            if not hasattr(self.config, 'lm_provider_params') or not self.config.lm_provider_params:
                raise ValueError("LM provider parameters are missing")
                
            if 'model_id' not in self.config.lm_provider_params:
                raise ValueError("model_id is required in LM provider parameters")
                
            logger.info(f"Initialized {self.name} with provider {self.config.lm_provider.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            # Clean up any resources if needed
            self._cleanup()
            raise
    

    @property
    def defaults(self):
        return PersonaDefaults(
            name="EmojiPersona",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="The emoji agent, that responds with emojis.",
            system_prompt="...",
        )

    async def process_message(self, message: Message):
        try:
            provider_name = self.config.lm_provider.name
            model_id = self.config.lm_provider_params["model_id"]
            
            # Use context manager for YChatHistory
            async with YChatHistory(ychat=self.ychat, k=2) as history:
                runnable = self.build_runnable()
                variables = JupyternautVariables(
                    input=message.body,
                    model_id=model_id,
                    provider_name=provider_name,
                    persona_name=self.name,
                )
                
                try:
                    variables_dict = variables.model_dump()
                    reply = runnable.invoke(variables_dict)
                    print(f"reply from model: {reply}")
                    
                    # Handle potential emoji conversion errors
                    try:
                        reply = emoji.emojize(reply, variant="emoji_type")
                        print(f"reply after emojize: {reply}")
                    except Exception as e:
                        logger.error(f"Error converting emojis: {str(e)}")
                        # Fall back to original reply if emoji conversion fails
                    
                    await self.send_message(reply)
                    
                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    logger.error(error_msg)
                    await self.send_message(error_msg)
                
        except Exception as e:
            logger.error(f"Fatal error in process_message: {str(e)}")
            raise

    def build_runnable(self) -> Any:
        llm = self.config.lm_provider(**self.config.lm_provider_params)
        
        runnable = PROMPT_TEMPLATE | llm | StrOutputParser()
        runnable = RunnableWithMessageHistory(
            runnable=runnable,  #  type:ignore[arg-type]
            get_session_history=lambda: YChatHistory(ychat=self.ychat, k=0),
            input_messages_key="input",
            history_messages_key="history",
        )
        return runnable