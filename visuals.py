import streamlit as st
from mermaid_graph import render_graph

def display_title():
    st.title("🧠 LangGraph LLM Chat")

def select_model():
    return st.radio("Select model", ["DeepSeek", "Claude"])

def get_user_input():
    return st.text_area("Enter your message:")

def display_parsed_output(parsed: str):
    st.text_area("Parsed Output", value=parsed, height=200)

def display_full_log(session_log: list):
    md_lines = []
    for entry in session_log:
        md_lines.append(f"## Query: {entry['query']}")
        md_lines.append("### Raw response")
        md_lines.append("```")
        md_lines.append(entry["raw"])
        md_lines.append("```")
        md_lines.append("### Parsed output")
        md_lines.append("```")
        md_lines.append(entry["parsed"])
        md_lines.append("```")
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
    model = select_model()
    user_input = get_user_input()
    if st.button("Submit") and user_input.strip():
        entry = chat_fn(user_input, model)
        session_log.append(entry)
        display_parsed_output(entry["parsed"])
        render_graph(entry["used_tools"])
        display_full_log(session_log)
