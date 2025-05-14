from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from lang_graph import agent_graph
import logging

logging.basicConfig(level=logging.DEBUG)

# Configure basic logging to capture messages
def chat_fn(message: str) -> dict:
    """
    Invokes the LangGraph agent with the user message.
    Extracts tool usage information for logging and visualization.
    """
    user_msg = HumanMessage(content=message)

    # Invoke the LangGraph agent.
    # We stream the graph to capture all intermediate steps/messages.
    # Use invoke to get the final state directly for non-streaming output
    logging.debug(f"--- [chat_service.py] Invoking agent_graph with message: {message}")
    final_state_dict = agent_graph.invoke({"messages": [user_msg]})
    logging.debug(f"--- [chat_service.py] agent_graph.invoke returned state: {final_state_dict}")

    final_messages = final_state_dict.get('messages', [])
    logging.debug(f"--- [chat_service.py] Extracted final_messages: {final_messages}")

    # Extract the last message from the final state as the parsed response
    final_parsed_response = "Error: Could not get response from agent."
    if final_messages and hasattr(final_messages[-1], 'content'):
        final_parsed_response = final_messages[-1].content

    tool_entries = []
    pending_tool_calls = {} # Store AIMessage tool_calls by id to match with ToolMessage

    for msg in final_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                pending_tool_calls[tc['id']] = {"name": tc['name'], "tool_input": tc['args'], "tool_output": "Error: Tool output not found"}
        elif isinstance(msg, ToolMessage):
            if msg.tool_call_id in pending_tool_calls:
                # This ToolMessage is the result of a pending tool call
                entry = pending_tool_calls.pop(msg.tool_call_id) # Remove from pending
                entry["name"] = msg.name # ToolMessage.name is the actual tool's name
                entry["tool_output"] = msg.content
                tool_entries.append(entry)

    # Add any remaining pending_tool_calls (should be rare if graph completes tool cycles)
    for _id, entry_data in pending_tool_calls.items():
        tool_entries.append(entry_data)
    logging.debug(f"--- [chat_service.py] Final tool_entries: {tool_entries}")

    used_tools_names = list(set(entry['name'] for entry in tool_entries))

    return {
      "query": message,
      "raw": "LangGraph Agent Invoked", # Indicate that the agent was used
      "parsed": final_parsed_response, # The final processed response
      "tool_entries": tool_entries,
      "used_tools": used_tools_names
    }
