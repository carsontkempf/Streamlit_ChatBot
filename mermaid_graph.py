import streamlit as st
from streamlit_mermaid import st_mermaid
from typing import List
import logging

logger = logging.getLogger(__name__)

# Counter for generating unique node IDs for Mermaid
_node_id_counter = 0

def _get_unique_node_id():
    global _node_id_counter
    _node_id_counter += 1
    return f"mmnode{_node_id_counter}" # mmnode for mindmap node

def build_mermaid(tool_entries: List[dict]) -> str:
    if not tool_entries:
        return "mindmap\n  root((No tool invocation steps to graph.))"

    mermaid_lines = ["mindmap"]
    mermaid_lines.append("  root((Tool Invocation Flow))")

    global _node_id_counter
    _node_id_counter = 0

    def sanitize_for_simple_mindmap_node(text: str, max_len: int = 0) -> str:
        s = str(text)

        s = s.replace("`", "'") # Replace backticks with single quotes
        s = s.replace('"', "'") # Replace double quotes with single quotes

        # Replace characters that define shapes or structures in Mermaid
        for char_to_replace in "(){}[]:;#":
            s = s.replace(char_to_replace, "_")

        # Newlines are not allowed in simple text node definitions, replace with space or similar
        s = s.replace("\n", " ")

        if max_len > 0 and len(s) > max_len:
            s = s[:max_len - 3] + "..."
        return s

    # parent_node_level is the indent level of the parent under which the current entries_subset will be added.
    def build_nodes_recursively(entries_subset: List[dict], parent_node_level: int):
        if not entries_subset:
            return

        entry = entries_subset[0]
        remaining_entries = entries_subset[1:]
        
        # Current tool's node level
        tool_node_level = parent_node_level + 1
        tool_node_indent = "  " * tool_node_level
        
        # Tool name as a simple node (less likely to have problematic characters)
        tool_node_id = _get_unique_node_id()
        entry_name = sanitize_for_simple_mindmap_node(str(entry.get("name", "Unknown Step")), 50)
        mermaid_lines.append(f"{tool_node_indent}{tool_node_id}[{entry_name}]")

        # Details as children of this tool node
        detail_node_level = tool_node_level + 1
        detail_node_indent = "  " * detail_node_level
        
        original_entry_name = entry.get("name", "Unknown Step")
        if original_entry_name == "tool_determination_router":
            prompt = sanitize_for_simple_mindmap_node(entry.get("router_llm_prompt", "N/A"), 60)
            raw_resp = sanitize_for_simple_mindmap_node(entry.get("router_llm_raw_response", "N/A"), 60)
            selected_tools = sanitize_for_simple_mindmap_node(str(entry.get("selected_tools_list", [])), 60)
            
            mermaid_lines.append(f'{detail_node_indent}{_get_unique_node_id()}[LLM Prompt: {prompt}]')
            mermaid_lines.append(f'{detail_node_indent}{_get_unique_node_id()}[LLM Raw Resp: {raw_resp}]')
            mermaid_lines.append(f'{detail_node_indent}{_get_unique_node_id()}[Selected Tools: {selected_tools}]')
        else: # Standard tool
            tool_input_str = str(entry.get("tool_input", "N/A"))
            tool_output_str = str(entry.get("tool_output", "N/A"))
            
            # Add "Input:" and "Output:" as simple text parent nodes for clarity
            input_parent_id = _get_unique_node_id()
            mermaid_lines.append(f'{detail_node_indent}{input_parent_id}[Input Details:]')
            input_lines = tool_input_str.split('\n')
            for line_num, line_content in enumerate(input_lines[:5]): # Show first 5 lines of input
                line_id = _get_unique_node_id()
                sanitized_line = sanitize_for_simple_mindmap_node(line_content, 70)
                mermaid_lines.append(f'{detail_node_indent}  {line_id}[{sanitized_line}]')

            output_parent_id = _get_unique_node_id()
            mermaid_lines.append(f'{detail_node_indent}{output_parent_id}[Output Details:]')
            output_lines = tool_output_str.split('\n')
            for line_num, line_content in enumerate(output_lines[:8]): # Show first 8 lines of output
                line_id = _get_unique_node_id()
                sanitized_line = sanitize_for_simple_mindmap_node(line_content, 70)
                mermaid_lines.append(f'{detail_node_indent}  {line_id}[{sanitized_line}]')

        # Add next tool as a child of the current tool node
        if remaining_entries:
            # The next tool is a child of the current tool node.
            build_nodes_recursively(remaining_entries, tool_node_level)

    if tool_entries:
        build_nodes_recursively(tool_entries, 1) # Initial parent is "root" at level 1

    return "\n".join(mermaid_lines)

def render_graph(tool_entries: List[dict]):
    if not tool_entries: # Add a check for empty tool_entries
        st.caption("No tool invocation steps to graph.")
        return
    mermaid_code = build_mermaid(tool_entries)


    st.text_area("Generated Mermaid Code:", value=mermaid_code, height=300)
    st.caption("Invocation Graph")
    st_mermaid(mermaid_code, height="800px") # Added height parameter