from langchain_core.prompts import ChatPromptTemplate as CPT

PROMPTS = {
    "define": CPT.from_messages([
        ("system", "Define the term in **one** sentence."),
        ("user", "{term}")
    ]),
    "summarize": CPT.from_messages([
        ("system", "Summarize the text in ≤{max_words} words."),
        ("user",   "{text}")
    ]),
    "recipe": CPT.from_messages([
        ("system", "Return a markdown recipe (title, ingredients, numbered steps, tips). Serve {servings} people."),
        ("user",   "{dish}")
    ]),
    "default": CPT.from_messages([
        ("system", "You are a helpful assistant."),
        ("user",   "{question}")
    ]),
}