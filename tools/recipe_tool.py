from langchain_core.tools import tool
from templates import PROMPTS # Assuming PROMPTS["recipe"] exists
from llm import get_llm # To invoke an LLM for the recipe

@tool(description="Finds or generates a recipe for a given dish, optionally for a specified number of servings. Use for recipe requests.")
def recipe_tool(dish: str, servings: int = 2) -> str:
    """
    Uses an LLM with a specific prompt to provide a recipe for the given dish and servings.
    """
    llm = get_llm("Claude") # Or "DeepSeek", or make it configurable
    prompt_template = PROMPTS.get("recipe")
    if not prompt_template:
        return "Error: Recipe prompt template not found."
    # Ensure your PROMPTS["recipe"] can handle 'dish' and 'servings'
    messages = prompt_template.format_messages(dish=dish, servings=servings)
    return llm.invoke(messages).content
