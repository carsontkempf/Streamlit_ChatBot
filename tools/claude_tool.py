from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from llm import get_llm # Import the function to get the LLM instance

@tool(
    description="A general-purpose tool that uses the Claude LLM to answer questions or generate text."
)
def claude_tool(query: str) -> str:
    """
    Invokes the Claude LLM with the given query.
    """
    claude_llm = get_llm("Claude") # Get the Claude LLM instance
    response = claude_llm.invoke([HumanMessage(content=query)])
    return response.content