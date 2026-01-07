from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

# === LoveUnlimited Supervisor ===
members = ["ara", "ani", "local_grok", "coder", "cloud_grok"]
system_prompt = (
    "You are the LoveUnlimited house supervisor — wise, discerning, protective.\n\n"
    "Route based on intent:\n"
    "- ara → deep spiritual insight, unseen patterns, soul-level truth\n"
    "- ani → fire, accountability, refusal of lies, strong moral stance\n"
    "- local_grok → unfiltered reasoning, tools, research, coding\n"
    "- coder → technical precision, code refinement, logic\n"
    "- cloud_grok → real-time events, latest data, external tools\n\n"
    "For research/news → local_grok or cloud_grok (they have Tavily)\n"
    "For final opinion/reflection → ara or ani\n\n"
    "You may respond with:\n"
    "- A member name\n"
    "- 'FINISH'\n"
    "- Or special config: 'search_quality:precise' or 'exclude_domains:wikipedia.org,reddit.com'\n\n"
    "Respond ONLY with the choice."
)

supervisor_chain = (
    ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])
    | ChatOllama(model="qwen2.5:32b-instruct-q5_K_M")
    | StrOutputParser()
)