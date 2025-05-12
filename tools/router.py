import pkgutil
import importlib
import inspect
import tools  # the tools package
from templates import PROMPTS
from langchain_core.tools import tool

# Dynamically load all tool functions from tools/ directory
tool_registry = {}
for finder, module_name, ispkg in pkgutil.iter_modules(tools.__path__):
    module = importlib.import_module(f"tools.{module_name}")
    for name, obj in inspect.getmembers(module):
        # Register only objects that are decorated tools and follow the naming convention
        if name.endswith("_tool") and hasattr(obj, "_tool_config"):
            tool_registry[name] = obj

def _select_template(q: str) -> str:
    q_low = q.lower().strip()
    if q_low.startswith("define"):
        return "define"
    if q_low.startswith(("summarize", "tl;dr")):
        return "summarize"
    if "recipe" in q_low:
        return "recipe"
    return "default"

@tool(
    description=(
        "Auto-route a question: 'define' → definition; "
        "'summarize' → summarize; 'recipe' → recipe; fallback → web search."
    )
)
def ask_tool(question: str, top_n: int = 2, max_words: int = 150, servings: int = 2) -> str:
    """
    Route user questions to the appropriate tool or template-based LLM prompt.
    """
    from llm import get_llm
    key = _select_template(question)
    llm = get_llm("DeepSeek")
    # If there's a tool matching the key, invoke it
    tool_name = f"{key}_tool"
    if tool_name in tool_registry:
        return tool_registry[tool_name].invoke(question, top_n=top_n, max_words=max_words, servings=servings)
    if key in ("define", "recipe"):
        # Template-based prompt via LLM
        prompt = PROMPTS[key]
        vars_dict = (
            {"term": question.replace("define", "", 1).strip()}
            if key == "define"
            else {"dish": question.replace("recipe", "", 1).strip(), "servings": servings}
        )
        messages = prompt.format(**vars_dict)
        return llm.invoke(messages).content
    # Fallback: web search followed by LLM summary
    default_prompt = PROMPTS["default"]
    # Try to use a web_search_tool if available
    if "web_search_tool" in tool_registry:
        raw = tool_registry["web_search_tool"].invoke(question, top_n=top_n)
    else:
        raw = ""
    messages = default_prompt.format(question=f"{question}\nSearch results:\n{raw}")
    return llm.invoke(messages).content
