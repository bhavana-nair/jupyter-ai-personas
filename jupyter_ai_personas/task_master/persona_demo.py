import abc
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models.base import BaseChatLLM
from langchain_core.prompts import BasePromptTemplate
from jupyter_ai import JupyterAI

# The JUPYTER_AI_CLASSES are not available in this environment, so we will create dummy classes for them
class DefaultPersona(JupyterAI):
    def _create_llm(self, *args, **kwargs) -> BaseChatLLM:
        pass
    def _create_pyprompt(self) -> BasePromptTemplate:
        return ChatPromptTemplate.from_template("{text}")
    def _create_prompt_template(self) -> BasePromptTemplate:
        return ChatPromptTemplate.from_template("{text}")

class CodeOptimizer(JupyterAI):
    def _create_llm(self, *args, **kwargs) -> BaseChatLLM:
        pass
    def _create_pyprompt(self) -> BasePromptTemplate:
        return ChatPromptTemplate.from_template("{text}")
    def _create_prompt_template(self) -> BasePromptTemplate:
        return ChatPromptTemplate.from_template("{text}")

class CustomPersona(JupyterAI, abc.ABC):
    """
    A base class for creating new personas.

    Subclasses must implement the following methods:
    - _create_llm(...)
    - _create_pyprompt(...)
    - _create_prompt_template(...)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def _create_llm(self, **kwargs) -> BaseChatLLM:
        """
        Create and return a LangChain LLM instance for this persona.
        This method should be implemented by subclasses to configure the
        specific language model they need.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _create_pyprompt(self) -> BasePromptTemplate:
        """
        Create and return a LangChain prompt template for Python code generation.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _create_prompt_template(self) -> BasePromptTemplate:
        """
        Create and return a general-purpose LangChain prompt template.
        """
        raise NotImplementedError

# Example of a subclass that fails to implement all abstract methods
try:
    class IncompletePersona(CustomPersona):
        def _create_llm(self, **kwargs) -> BaseChatLLM:
            # This would be a real LLM implementation
            return None
    
    incomplete_persona = IncompletePersona()
except TypeError as e:
    print(f"Successfully caught expected error:\n{e}")

# Example of a valid subclass
class MyPersona(CustomPersona):
    def _create_llm(self, **kwargs) -> BaseChatLLM:
        # In a real scenario, you would instantiate and return a specific LLM
        # from langchain, e.g., ChatOpenAI()
        print("MyPersona._create_llm() called")
        return None # Returning None for demonstration purposes

    def _create_pyprompt(self) -> BasePromptTemplate:
        print("MyPersona._create_pyprompt() called")
        return ChatPromptTemplate.from_template("Translate the following Python code: {code}")

    def _create_prompt_template(self) -> BasePromptTemplate:
        print("MyPersona._create_prompt_template() called")
        return ChatPromptTemplate.from_template("You are a helpful assistant. {question}")

# This demonstrates that a correctly implemented subclass can be instantiated
my_persona = MyPersona()
my_persona._create_llm()
my_persona._create_pyprompt()
my_persona._create_prompt_template()

result = "Demonstration complete. The CustomPersona abstract class works as expected."