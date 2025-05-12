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
        # Escape line breaks for Mermaid label
        label = entry["name"] + "\\nIn: " + entry["input"].replace('"', '\\"') + "\\nOut: " + entry["output"].replace('"', '\\"')
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
    mermaid_code = build_mermaid(tool_entries)
    st.caption("Invocation Graph")
    st_mermaid(mermaid_code)
