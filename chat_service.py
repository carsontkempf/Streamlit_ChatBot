import json
from langchain_core.messages import HumanMessage, AIMessage
from llm import get_llm
from tools.router import ask_tool   # the auto-discovered “ask_tool”

def chat_fn(message: str, model: str) -> dict:
    user_msg = HumanMessage(content=message)
    llm = get_llm(model)

    # start with the LLM as first "tool"
    tool_entries = []

    # 1) LLM → raw
    ai_msg: AIMessage = llm.invoke([user_msg])
    raw_response = ai_msg.content
    tool_entries.append({
      "name": model.lower(),
      "input": message,
      "output": raw_response
    })

    # 2) if LLM asked for a tool call, route via ask_tool
    if getattr(ai_msg, "tool_calls", None):
        parsed = ask_tool(message)
        tool_entries.append({
          "name": "ask_tool",
          "input": message,
          "output": parsed
        })
    else:
        parsed = raw_response

    return {
      "query": message,
      "raw": raw_response,
      "parsed": parsed,
      "tool_entries": tool_entries
    }