import os
import json
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict
import streamlit as st
from streamlit_mermaid import st_mermaid

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
from tools import tools, tavily_search_tool, summarize_tool, ask, _select_template
from templates import PROMPTS


# Load environment variables
load_dotenv()
DEEPSEEK_API_KEY = st.sidebar.text_input("DeepSeek API Key", type="password") or os.getenv("DEEPSEEK_API_KEY")
ANTHROPIC_API_KEY = st.sidebar.text_input("Anthropic API Key", type="password") or os.getenv("ANTHROPIC_API_KEY")

# Define state schema
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class GraphState(TypedDict):
    pass

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

def build_tools_templates_graph():
    builder = StateGraph(GraphState)
    # Add start and end
    def noop(state): return {}
    builder.add_node("start", noop)
    builder.add_node("end", noop)
    builder.add_edge(START, "start")
    for tool_name in ["tavily_search_tool", "summarize_tool", "ask"]:
        builder.add_node(tool_name, noop)
        builder.add_edge("start", tool_name)
        builder.add_edge(tool_name, "end")
    for template_name in PROMPTS:
        node_name = f"{template_name}_template"
        builder.add_node(node_name, noop)
        builder.add_edge("start", node_name)
        builder.add_edge(node_name, "end")
    return builder.compile()

def make_invocation_builder():
    builder = StateGraph(GraphState)
    def noop(state): return {}
    builder.add_node("start", noop)
    builder.add_node("end", noop)
    builder.add_edge(START, "start")
    for tool_name in ["tavily_search_tool", "summarize_tool", "ask"]:
        builder.add_node(tool_name, noop)
        builder.add_edge("start", tool_name)
        builder.add_edge(tool_name, "end")
    for tpl in PROMPTS:
        node = f"{tpl}_template"
        builder.add_node(node, noop)
        builder.add_edge("start", node)
        builder.add_edge(node, "end")
    return builder

def chat_fn(message: str, model: str) -> str:
    user_msg = HumanMessage(content=message)
    llm = llm_deepseek if model == "DeepSeek" else llm_claude

    # Always include the LLM as a node
    used_tools = [model.lower()]
    used_templates = []

    # Phase 1: LLM generates response or tool call
    ai_msg: AIMessage = llm.invoke([user_msg])

    # Determine if a tool was requested
    tool_calls = getattr(ai_msg, "tool_calls", None)
    if tool_calls:
        call = tool_calls[0]
        if "function" in call:
            func_info = call["function"]
            name = func_info.get("name")
            raw_args = func_info.get("arguments", "{}")
        else:
            name = call.get("name")
            raw_args = call.get("args", "{}")
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

        tool_map = {
            "tavily_search_tool": tavily_search_tool,
            "summarize_tool":    summarize_tool,
            "ask":               ask,
        }
        tool_fn = tool_map.get(name)
        if not tool_fn:
            output = f"Unknown tool: {name}"
        else:
            output = invoke_tool_graph(tool_fn, ai_msg)
            used_tools.append(name)
            # If using 'ask', determine which template was used
            if name == "ask":
                tpl_key = _select_template(message)
                used_templates = [f"{tpl_key}_template"]
    else:
        # No tool → simple LLM response
        output = ai_msg.content

    # Deduplicate used_tools
    used_tools = list(dict.fromkeys(used_tools))

    # Build and render dynamic invocation graph
    edges = []
    for tn in used_tools:
        edges.append(f"start --> {tn};")
        edges.append(f"{tn} --> end_node;")
    for tpl in used_templates:
        edges.append(f"start --> {tpl};")
        edges.append(f"{tpl} --> end_node;")
    mermaid_code = (
        "graph LR;\n"
        "start((start));\n"
        "end_node((end));\n"
        + "\n".join(edges) +
        ";"
    )
    st.caption("Invocation Graph")
    st_mermaid(mermaid_code)

    return output

st.title("🧠 LangGraph LLM Chat")
model = st.radio("Select model", ["DeepSeek", "Claude"])
user_input = st.text_area("Enter your message:")
if st.button("Submit") and user_input.strip():
    response = chat_fn(user_input, model)
    st.text_area("Response", value=response, height=300)