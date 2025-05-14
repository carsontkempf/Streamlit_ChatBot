import streamlit as st
from streamlit_mermaid import st_mermaid
from typing import List

def build_mermaid(tool_entries: List[dict]) -> str:
    # tool_entries: list of dicts with keys 'name', 'input', 'output'
    nodes = []
    edges = []
    # start node
    mermaid_code = "graph LR;\nstart((start));\nend_node((end));\n"
    for i, entry in enumerate(tool_entries):
        node_id = f"tool{i}"
        entry_name = entry.get("name", "Unknown Step")

        if entry_name == "tool_determination_router":
            # Special formatting for the router step
            prompt_short = str(entry.get("router_llm_prompt", "N/A"))[:50] + "..." # Keep it brief for the graph
            response_short = str(entry.get("router_llm_raw_response", "N/A"))[:50] + "..."
            selected_list = entry.get("selected_tools_list", [])
            label = (f"{entry_name}\\n"
                       f"Prompt: {prompt_short.replace('"', '\\"')}\\n"
                       f"Raw Resp: {response_short.replace('"', '\\"')}\\n"
                       f"Selected: {str(selected_list).replace('"', '\\"')}")
        else:
            # Standard formatting for other tools/steps
            tool_input_str = str(entry.get("tool_input", "N/A")).replace('"', '\\"')
            tool_output_str = str(entry.get("tool_output", "N/A")).replace('"', '\\"')
            label = f"{entry_name}\\nIn: {tool_input_str}\\nOut: {tool_output_str}"

        nodes.append(f'{node_id}["{label}"];')
        if i == 0:
            edges.append(f"start --> {node_id};")
        else:
            edges.append(f"tool{i-1} --> {node_id};")
    # connect last tool to end
    if tool_entries:
        edges.append(f"tool{len(tool_entries)-1} --> end_node;")
    mermaid_code += "\n".join(nodes + edges)
    return mermaid_code

def render_graph(tool_entries: List[dict]):
    if not tool_entries: # Add a check for empty tool_entries
        st.caption("No tool invocation steps to graph.")
        return
    mermaid_code = build_mermaid(tool_entries)
    st.caption("Invocation Graph")
    st_mermaid(mermaid_code)