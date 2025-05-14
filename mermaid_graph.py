import streamlit as st
from streamlit_mermaid import st_mermaid
from typing import List

def build_mermaid(tool_entries: List[dict]) -> str:
    if not tool_entries:
        return "mindmap\n  root((No tool invocation steps to graph.))"

    mermaid_lines = ["mindmap"]
    # Add a root node for the mindmap.
    # Shapes can be: ((circle)), (rounded), [square], default (no brackets)
    mermaid_lines.append("  root((Tool Invocation Flow))") # Main root, level 1 (indent "  ")

    # Helper to sanitize text and optionally truncate
    def sanitize(text: str, max_len: int = 0) -> str:
        s = str(text)
        if max_len > 0 and len(s) > max_len:
            s = s[:max_len-3] + "..."
        # Mindmap simple text nodes handle newlines naturally.
        # Avoid characters that might break simple line-based parsing.
        # For now, assume content is relatively clean.
        return s

    # Recursively build the mindmap structure
    # parent_node_level is the indent level of the parent under which the current entries_subset will be added.
    def build_nodes_recursively(entries_subset: List[dict], parent_node_level: int):
        if not entries_subset:
            return

        entry = entries_subset[0]
        remaining_entries = entries_subset[1:]
        
        # Current tool's node level
        tool_node_level = parent_node_level + 1
        tool_node_indent = "  " * tool_node_level
        
        entry_name = sanitize(entry.get("name", "Unknown Step"))
        mermaid_lines.append(f"{tool_node_indent}{entry_name}")

        # Details as children of this tool node
        detail_node_level = tool_node_level + 1
        detail_node_indent = "  " * detail_node_level
        
        original_entry_name = entry.get("name", "Unknown Step") # Use original for condition
        if original_entry_name == "tool_determination_router":
            prompt = sanitize(entry.get("router_llm_prompt", "N/A"), 100)
            raw_resp = sanitize(entry.get("router_llm_raw_response", "N/A"), 100)
            selected_tools = sanitize(str(entry.get("selected_tools_list", [])), 100)
            mermaid_lines.append(f"{detail_node_indent}LLM Prompt: {prompt}")
            mermaid_lines.append(f"{detail_node_indent}LLM Raw Resp: {raw_resp}")
            mermaid_lines.append(f"{detail_node_indent}Selected Tools: {selected_tools}")
        else: # Standard tool
            tool_input = sanitize(entry.get("tool_input", "N/A"), 70)
            tool_output = sanitize(entry.get("tool_output", "N/A"), 70)
            mermaid_lines.append(f"{detail_node_indent}Input: {tool_input}")
            mermaid_lines.append(f"{detail_node_indent}Output: {tool_output}")

        # Add next tool as a child of the current tool node
        if remaining_entries:
            # The next tool is a child of the current tool node.
            # So, its parent is the current tool node (at tool_node_level).
            build_nodes_recursively(remaining_entries, tool_node_level)

    if tool_entries:
        build_nodes_recursively(tool_entries, 1) # Initial parent is "root" at level 1

    return "\n".join(mermaid_lines)

def render_graph(tool_entries: List[dict]):
    if not tool_entries: # Add a check for empty tool_entries
        st.caption("No tool invocation steps to graph.")
        return
    mermaid_code = build_mermaid(tool_entries)
    st.caption("Invocation Graph")
    st_mermaid(mermaid_code)