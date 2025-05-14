import streamlit as st
from mermaid_graph import render_graph
# from typing import List # Not strictly needed if not type hinting elsewhere in this file
def display_title():
    st.title("🧠 LLM Chat with Tool Routing")

def get_user_input():
    return st.text_area("Enter your message:")

# display_parsed_output is defined but not used in ui_main.
# If you intend to use it, you can uncomment it and call it.
# def display_parsed_output(parsed: str):
#     st.text_area("Parsed Output", value=parsed, height=200)

def display_full_log(session_log: list):
    md_lines = []
    for i, overall_entry in enumerate(session_log):
        md_lines.append(f"# Interaction {i+1}")
        md_lines.append(f"## User Query: {overall_entry['query']}")
        md_lines.append("---")
        md_lines.append("### Tool Execution Log:")

        for step_idx, tool_step in enumerate(overall_entry.get("tool_entries", [])):
            md_lines.append(f"#### Step {step_idx + 1}: {tool_step['name']}")
            if tool_step["name"] == "tool_determination_router":
                md_lines.append("**Router LLM Prompt:**")
                md_lines.append("```text")
                md_lines.append(str(tool_step.get("router_llm_prompt", "N/A")))
                md_lines.append("```")
                md_lines.append("**Router LLM Raw Response:**")
                md_lines.append("```text")
                md_lines.append(str(tool_step.get("router_llm_raw_response", "N/A")))
                md_lines.append("```")
                md_lines.append(f"**Selected Tools List:** `{tool_step.get('selected_tools_list', [])}`")
            else: # For other tools
                md_lines.append("**Tool Input:**")
                md_lines.append("```text")
                md_lines.append(str(tool_step.get("tool_input", "N/A")))
                md_lines.append("```")
                md_lines.append("**Tool Output:**")
                md_lines.append("```text")
                md_lines.append(str(tool_step.get("tool_output", "N/A")))
                md_lines.append("```")
            md_lines.append("---")

        md_lines.append("### Final Parsed Output:")
        if overall_entry.get("parsed"):
            md_lines.append("```")
            md_lines.append(overall_entry["parsed"])
            md_lines.append("```")
        else:
            md_lines.append("*(No final parsed output)*")
        md_lines.append("")
    md_content = "\n".join(md_lines)
    st.write("**Full interaction log (Markdown):**")
    st.markdown(md_content)

def ui_main(chat_fn):
    """Main UI orchestration."""
    if "log" not in st.session_state:
        st.session_state["log"] = []
    session_log = st.session_state["log"]
    display_title()
    user_input = get_user_input()
    if st.button("Submit") and user_input.strip():
        entry = chat_fn(user_input)
        session_log.append(entry)
        # Ensure "tool_entries" exists and is a list before rendering
        tool_entries_for_graph = entry.get("tool_entries", [])
        if isinstance(tool_entries_for_graph, list):
            render_graph(tool_entries_for_graph)
        else:
            st.warning("Graph data (tool_entries) is not in the expected list format.")
        display_full_log(session_log)
