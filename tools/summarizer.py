from langchain_core.tools import tool

@tool(
    description="Summarize the input text to at most max_words words."
)
def summarize_tool(text: str, max_words: int = 150) -> str:
    """
    Summarize the input text by returning up to max_words words.
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."
