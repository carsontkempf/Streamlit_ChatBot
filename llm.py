from config import DEEPSEEK_API_KEY, ANTHROPIC_API_KEY
from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
from tools import tools as tool_list

__all__ = ["get_llm"]


# Initialize DeepSeek LLM with tools
llm_deepseek = ChatDeepSeek(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    temperature=0.25,
    max_tokens=8192,
)

if tool_list:
    llm_deepseek.bind_tools(tool_list)


# Initialize Claude LLM with tools
llm_claude = ChatAnthropic(
    api_key=ANTHROPIC_API_KEY,
    model="claude-3-7-sonnet-20250219",
    temperature=0.0,
    max_tokens=1024,
)

if tool_list:
    llm_claude.bind_tools(tool_list)

def get_llm(model_name: str):
    """
    Return the appropriate LLM instance based on model_name.
    Supported models: "DeepSeek", "Claude".
    """
    if model_name == "DeepSeek":
        return llm_deepseek
    elif model_name == "Claude":
        return llm_claude
    else:
        raise ValueError(f"Unknown model name: {model_name}")
