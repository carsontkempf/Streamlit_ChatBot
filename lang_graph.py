from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from typing import Annotated, Sequence, TypedDict
# Imports for llm and tools will be moved into the one-time initialization block
import logging

# --- Module-level flag and logger setup ---
_LANG_GRAPH_INITIALIZATION_RAN = False
logger = logging.getLogger(__name__) # Use standard __name__ for the logger

# Configure basic logging ONCE. Best in app entry point, but can be here defensively.
if not logging.getLogger().hasHandlers(): # Check if root logger is already configured
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"--- [{__name__}] Root logger basicConfig applied by lang_graph.py as it was not yet configured. ---")
else:
    logger.info(f"--- [{__name__}] Root logger basicConfig already present. ---")

# Ensure this module's logger is at least DEBUG for its own messages
if logger.getEffectiveLevel() > logging.DEBUG: # getEffectiveLevel considers parent loggers
    logger.setLevel(logging.DEBUG)
    logger.info(f"--- [{__name__}] Logger level for '{__name__}' set to DEBUG. ---")


# ------------ LangGraph ------------

# The state will track the conversation history
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# ------------ LLM, Tools, and Graph Components (Initialized Once) ------------
# Declare module-level variables that will be set during one-time initialization.
agent_llm_name = "DeepSeek" # Or "Claude"
core_llm = None
llm_with_tools = None
available_tools = []
tool_node = None # Define tool_node here
agent_graph = None # Define agent_graph here

# This node takes the state (messages) and invokes the LLM with tools
def call_model(state: AgentState):
    # This function uses the module-level `llm_with_tools` initialized above.
    if llm_with_tools is None:
        # This indicates a critical failure in the one-time initialization.
        logger.critical(f"--- [{__name__} call_model CRITICAL] llm_with_tools is None! Initialization may have failed or was bypassed.")
        # Depending on desired robustness, either raise an error or attempt a fallback.
        # Raising an error is often better to highlight the configuration issue.
        raise RuntimeError("LangGraph's llm_with_tools was not initialized properly.")

    messages = state['messages']
    # The LLM will decide if it needs to call a tool based on the messages and bound tools
    response = llm_with_tools.invoke(messages)
    # These are runtime logs, expected to appear on each invocation of call_model
    logger.debug(f"--- [{__name__} call_model RUNTIME] LLM response object: {response}")
    if hasattr(response, 'tool_calls') and response.tool_calls:
        logger.debug(f"--- [{__name__} call_model RUNTIME] LLM response has tool_calls: {response.tool_calls}")
    else:
        logger.debug(f"--- [{__name__} call_model RUNTIME] LLM response has NO tool_calls.")
    return {"messages": [response]}

core_llm = None
llm_with_tools = None
available_tools = []
tool_node = None # Define tool_node here
agent_graph = None # Define agent_graph here

if not _LANG_GRAPH_INITIALIZATION_RAN:
    logger.info(f"--- [{__name__} ONE-TIME INIT START] Initializing LangGraph components. ---")

    # Moved imports to be part of the one-time execution block
    # This is useful if these imports are costly or have side-effects.
    from llm import get_llm
    from tools import tool_box

    core_llm = get_llm(agent_llm_name) # Assign to module-level core_llm
    logger.debug(f"--- [{__name__} ONE-TIME INIT] tool_box from tools: {tool_box}")

    # Assign to module-level `available_tools`
    available_tools = list(tool_box.values()) if tool_box else []
    logger.debug(f"--- [{__name__} ONE-TIME INIT] available_tools (names): {[tool.name for tool in available_tools if hasattr(tool, 'name')]}")

    if available_tools:
        llm_with_tools = core_llm.bind_tools(available_tools) # Assign to module-level llm_with_tools
        logger.debug(f"--- [{__name__} ONE-TIME INIT] LLM bound with tools: {[tool.name for tool in available_tools if hasattr(tool, 'name')]}")
    else:
        llm_with_tools = core_llm # Assign to module-level llm_with_tools
        logger.warning(f"--- [{__name__} ONE-TIME INIT] Warning: No tools found in tool_box. The agent LLM ({agent_llm_name}) will not be able to call tools.")

    # ToolNode must be created after available_tools is populated.
    tool_node = ToolNode(available_tools) # Assign to module-level tool_node
    logger.debug(f"--- [{__name__} ONE-TIME INIT] ToolNode created. ---")

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
    logger.info(f"--- [{__name__} ONE-TIME INIT] LangGraph workflow compiled. ---")

    _LANG_GRAPH_INITIALIZATION_RAN = True
    logger.info(f"--- [{__name__} ONE-TIME INIT COMPLETE] LangGraph components initialized. ---")
else:
    logger.info(f"--- [{__name__}] LangGraph components already initialized. Skipping one-time setup. ---")

# You can optionally add a checkpointer here for memory across turns
# from langgraph.checkpoint.memory import MemorySaver
# memory = MemorySaver()
# agent_graph = workflow.compile(checkpointer=memory)

# Export the compiled graph for use in chat_service.py
__all__ = ["agent_graph"]