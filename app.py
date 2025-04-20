import os
import logging
import json
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict

import gradio as gr
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
from tools import tools, tavily_search_tool, summarize_tool, ask

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Define state schema
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Initialize LLMs and bind tools
llm_deepseek = ChatDeepSeek(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    temperature=0.25,
    max_tokens=8192,
).bind_tools(tools)

llm_claude = ChatAnthropic(
    api_key=ANTHROPIC_API_KEY,
    model="claude-3-7-sonnet-20250219",
    temperature=0.0,
    max_tokens=1024,
).bind_tools(tools)

def invoke_tool_graph(tool_fn, ai_msg: AIMessage) -> str:
    """
    Build and run a minimal graph that invokes a single tool, seeded with the AIMessage.
    """
    builder = StateGraph(ChatState)
    builder.add_node("invoke_tool", ToolNode([tool_fn]))
    builder.add_edge(START, "invoke_tool")
    graph = builder.compile()
    result = graph.invoke({"messages": [ai_msg]})
    return result["messages"][-1].content

def chat_fn(message: str, model: str) -> str:
    logging.debug(f"chat_fn received message='{message}' model='{model}'")
    user_msg = HumanMessage(content=message)
    llm = llm_deepseek if model == "DeepSeek" else llm_claude

    # Phase 1: LLM generates response or tool call
    ai_msg: AIMessage = llm.invoke([user_msg])
    logging.debug(f"LLM response: {ai_msg}")

    # Phase 2: If a tool was requested, extract and run it
    tool_calls = getattr(ai_msg, "tool_calls", None)
    if tool_calls:
        call = tool_calls[0]
        # Determine tool name and arguments from either structure
        if "function" in call:
            func_info = call["function"]
            name = func_info.get("name")
            raw_args = func_info.get("arguments", "{}")
        else:
            name = call.get("name")
            raw_args = call.get("args", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        logging.debug(f"Invoking tool '{name}' with args={args}")

        tool_map = {
            "tavily_search_tool": tavily_search_tool,
            "summarize_tool":    summarize_tool,
            "ask":               ask,
        }
        tool_fn = tool_map.get(name)
        if not tool_fn:
            return f"Unknown tool: {name}"

        return invoke_tool_graph(tool_fn, ai_msg)

    # No tool requested → return raw content
    return ai_msg.content

# Launch the Gradio interface
gr.Interface(
    fn=chat_fn,
    inputs=[
        gr.Textbox(label="Message"),
        gr.Radio(["DeepSeek", "Claude"], label="Model")
    ],
    outputs=gr.Textbox(label="Response"),
    title="Custom GPT Chat"
).launch()