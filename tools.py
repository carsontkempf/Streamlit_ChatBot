import os
import json
from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import TavilyClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
import templates

load_dotenv()

# ── API keys ──────────────────────────────────────────────────────────────────
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# ── clients ───────────────────────────────────────────────────────────────────
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
llm           = ChatDeepSeek(model="deepseek-chat", api_key=DEEPSEEK_API_KEY)

# ── Tool 1: Tavily web search ────────────────────────────────────────────────
@tool(
    description="Web search using Tavily; returns JSON string of top_n results."
)
def tavily_search_tool(query: str, top_n: int = 2) -> str:
    try:
        res = tavily_client.search(query)
        if isinstance(res, list) and top_n > 0:
            res = res[:top_n]
        return json.dumps(res, indent=2)
    except Exception as exc:
        return f"Error during search: {exc}"

# ── Tool 2: Lightweight summarizer ───────────────────────────────────────────
@tool(
    description="Summarize the input text to at most max_words words."
)
def summarize_tool(text: str, max_words: int = 150) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words]) + "..."

# ── router helpers ────────────────────────────────────────────────────────────
def _select_template(q: str) -> str:
    q_low = q.lower().strip()
    if q_low.startswith("define"):
        return "define"
    if q_low.startswith(("summarize", "tl;dr")):
        return "summarize"
    if "recipe" in q_low:
        return "recipe"
    return "default"

# ── Tool 3: ask ──────────────────────────────────────────────────────────────
@tool(
    description=(
        "Auto‑route a question: 'define' → definition; "
        "'summarize' → summarize; 'recipe' → recipe; fallback → web search."
    )
)
def ask(question: str, top_n: int = 2, max_words: int = 150, servings: int = 2) -> str:
    key = _select_template(question)
    if key == "summarize":
        return summarize_tool(question, max_words)
    if key in ("define", "recipe"):
        prompt: ChatPromptTemplate = templates.PROMPTS[key]
        vars_dict = (
            {"term": question.replace("define", "", 1).strip()}
            if key == "define"
            else {"dish": question.replace("recipe", "", 1).strip(), "servings": servings}
        )
        msg_list = prompt.format(**vars_dict)
        return llm.invoke(msg_list).content
    return tavily_search_tool(question, top_n)

# ── export list ───────────────────────────────────────────────────────────────
tools = [tavily_search_tool, summarize_tool, ask]