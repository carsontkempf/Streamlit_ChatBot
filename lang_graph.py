from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, AIMessage
from typing import Annotated, Sequence, TypedDict
from templates import PROMPTS

# ------------ LangGraph ------------

class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class GraphState(TypedDict):
    pass

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
    """
    Build a graph connecting start, tool nodes, template nodes, and end.
    """
    builder = StateGraph(GraphState)
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
    """
    Return an uncompiled graph builder for flexible invocation sequences.
    """
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