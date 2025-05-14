from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from llm import get_llm # Import the function to get the LLM instance

@tool(
    description="A general-purpose tool that uses the DeepSeek LLM to answer questions or generate text."
)
def deepseek_tool(query: str) -> str:
    """
    Invokes the DeepSeek LLM with the given query.
    """
    deepseek_llm = get_llm("DeepSeek") # Get the DeepSeek LLM instance
    response = deepseek_llm.invoke([HumanMessage(content=query)])
    return response.content