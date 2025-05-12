import json
from config import TAVILY_API_KEY
from tavily import TavilyClient
from langchain_core.tools import tool

# Initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# Perform a web search using Tavily and return the top_n results as a JSON string.

@tool(
    description="Web search using Tavily; returns JSON string of top_n results."
)
def tavily_search_tool(query: str, top_n: int = 2) -> str:
    """
    Perform a web search using Tavily and return the top_n results as a JSON string.
    """
    try:
        results = tavily_client.search(query)
        if isinstance(results, list) and top_n > 0:
            results = results[:top_n]
        return json.dumps(results, indent=2)
    except Exception as exc:
        return f"Error during web search: {exc}"
