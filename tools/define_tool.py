from langchain_core.tools import tool
from llm import get_llm # To invoke an LLM for the definition
# Assuming you might have a templates.py for specific prompt structures,
# otherwise, we can define a simple prompt here.
# from templates import PROMPTS

@tool(description="Defines a given term or concept. Use this when asked to define something (e.g., 'define X').")
def define_tool(term: str) -> str:
    """
    Uses an LLM with a specific prompt to define the provided term.
    """
    # You might want to choose a specific LLM or use the one selected by the user
    llm = get_llm("Claude") # Or "DeepSeek", or make it configurable
    
    # Simple prompt for definition
    prompt_content = f"Please provide a concise definition for the term: {term}"
    
    # Assuming get_llm returns a LangChain LLM object that can be invoked with a string
    return llm.invoke(prompt_content).content