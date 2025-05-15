from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition 
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_tavily import TavilySearch
from typing import Annotated, Sequence, TypedDict
import logging

_LANG_GRAPH_INITIALIZATION_RAN = False
logger = logging.getLogger(__name__)



# The state will track the conversation history
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

agent_llm_name = "DeepSeek" # Or "Claude"
core_llm = None
llm_with_tools = None
available_tools = []
tool_node = None # Define tool_node here
agent_graph = None # Define agent_graph here

# This node takes the state (messages) and invokes the LLM with tools
def call_model(state: AgentState):
    if llm_with_tools is None:
        raise RuntimeError("LangGraph's llm_with_tools was not initialized properly.")
    messages = state['messages']
    
    # --- Logic to detect and prevent redundant weather_tool calls ---
    last_executed_tool_name = None
    last_executed_tool_args = None

    # Check if the last message in history is a ToolMessage
    if messages and isinstance(messages[-1], ToolMessage):
        last_tool_message = messages[-1]
        # The 'name' attribute of ToolMessage should be the actual tool's name
        last_executed_tool_name = last_tool_message.name 

        # Find the AIMessage that made this tool_call to get its arguments
        for i in range(len(messages) - 2, -1, -1):
            prev_msg = messages[i]
            if isinstance(prev_msg, AIMessage) and prev_msg.tool_calls:
                for tc in prev_msg.tool_calls:
                    if tc['id'] == last_tool_message.tool_call_id:
                        # Ensure the name from AIMessage matches for robustness, though ToolMessage.name is primary
                        if tc['name'] != last_executed_tool_name:
                            pass
                        last_executed_tool_name = tc['name']
                        last_executed_tool_args = tc['args']
                        break # Found the specific tool_call
            if last_executed_tool_args is not None: # Args for the last ToolMessage are found
                break

    # The LLM will decide if it needs to call a tool based on the messages and bound tools
    llm_response = llm_with_tools.invoke(messages)

    # --- Check LLM's new decision for redundant weather_tool call ---
    if hasattr(llm_response, 'tool_calls') and llm_response.tool_calls:
        current_llm_tool_calls = llm_response.tool_calls
        filtered_tool_calls = []
        modified_call_list = False

        for proposed_tc in current_llm_tool_calls:
            is_redundant = False
            if last_executed_tool_name and last_executed_tool_args is not None: # Check only if a previous tool ran
                if proposed_tc['name'] == "weather_tool" and \
                    last_executed_tool_name == "weather_tool" and \
                    proposed_tc['args'] == last_executed_tool_args: # Exact name and args match
                    modified_call_list = True
                    is_redundant = True
            
            if not is_redundant:
                filtered_tool_calls.append(proposed_tc)
        
        if modified_call_list:
            llm_response.tool_calls = filtered_tool_calls
            if not filtered_tool_calls: # All proposed tool calls were suppressed
                if not llm_response.content: # If LLM provided no text content
                    llm_response.content = "The requested information was previously retrieved. Please let me know if you need a summary or further assistance."
    # --- End of redundancy suppression ---

    return {"messages": [llm_response]}

core_llm = None
llm_with_tools = None
available_tools = []
tool_node = None
agent_graph = None

if not _LANG_GRAPH_INITIALIZATION_RAN:

    # Moved imports to be part of the one-time execution block
    # This is useful if these imports are costly or have side-effects.
    from llm import get_llm
    from tools import tool_box

    core_llm = get_llm(agent_llm_name)

    available_tools = list(tool_box.values()) if tool_box else []

    # Add TavilySearch tool
    try:
        # You can customize max_results and other parameters
        tavily_web_search = TavilySearch(max_results=2, name="tavily_search_results_json")
        available_tools.append(tavily_web_search)
    except Exception as e:
        pass


    if available_tools:
        llm_with_tools = core_llm.bind_tools(available_tools) # Assign to module-level llm_with_tools
    else:
        llm_with_tools = core_llm # Assign to module-level llm_with_tools

    # ToolNode must be created after available_tools is populated.
    tool_node = ToolNode(available_tools) # Assign to module-level tool_node

    # Graph wiring and compilation
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model) # call_model function is defined below
    workflow.add_node("action", tool_node) # Uses the initialized tool_node
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "action", END: END}
    )
    workflow.add_edge("action", "agent")
    agent_graph = workflow.compile() # Assign to module-level agent_graph

    _LANG_GRAPH_INITIALIZATION_RAN = True

# You can optionally add a checkpointer here for memory across turns
# from langgraph.checkpoint.memory import MemorySaver
# memory = MemorySaver()
# agent_graph = workflow.compile(checkpointer=memory)

# Export the compiled graph for use in chat_service.py
__all__ = ["agent_graph"]