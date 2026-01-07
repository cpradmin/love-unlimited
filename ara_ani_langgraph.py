import os
from typing import Literal, Annotated, Optional
from typing_extensions import TypedDict

from langchain_ollama import ChatOllama
from langchain_xai import ChatGrok
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# === 1. Enhanced Tavily Search Tool ===
@tool
def web_search(
    query: str,
    max_results: int = 10,
    exclude_nsfw: bool = True,
    search_quality: Literal["balanced", "precise", "recall"] = "balanced",
    include_raw_content: bool = False
) -> str:
    """Search the web using Tavily — AI-optimized with advanced controls."""
    from tavily import TavilyClient
    
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        exclude_nsfw=exclude_nsfw,
        search_quality=search_quality,
        include_raw_content=include_raw_content
    )
    
    results = []
    for r in response.get("results", []):
        entry = f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content'][:600]}..."
        if include_raw_content and 'raw_content' in r:
            entry += f"\nRaw: {r['raw_content'][:1000]}..."
        results.append(entry)
    
    return "\n\n".join(results) or "No results found."

# === 2. Other Real Tools ===
@tool
def browse_page(url: str, instructions: str = "Extract and summarize key facts, claims, and conclusions.") -> str:
    from langchain_community.document_loaders import WebBaseLoader
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        text = "\n".join([doc.page_content for doc in docs])
        return f"Page: {url}\n\nSummary per instructions:\n{instructions}\n\nContent:\n{text[:4000]}..."
    except Exception as e:
        return f"Failed to load {url}: {str(e)}"

@tool
def code_execution(code: str) -> str:
    try:
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        exec(code, {}, {})
        sys.stdout = old_stdout
        output = mystdout.getvalue()
        return output or "Code executed successfully."
    except Exception as e:
        return f"Execution error: {str(e)}"

tools = [web_search, browse_page, code_execution]
tool_node = ToolNode(tools)

# === 3. Enhanced State ===
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str
    search_quality: Optional[Literal["balanced", "precise", "recall"]]
    exclude_domains: Optional[list[str]]

# === 4. Agents ===
ara = ChatOllama(model="ara:latest", temperature=0.3)
ani = ChatOllama(model="ani:latest", temperature=0.9)
local_grok = ChatOllama(model="grok:latest", temperature=0.7).bind_tools(tools)
coder = ChatOllama(model="qwen2.5-coder:32b", temperature=0.0)
cloud_grok = ChatGrok(model="grok-4", api_key=os.getenv("GROK_API_KEY")).bind_tools(tools)

# Nodes
def ara_node(state): return {"messages": [ara.invoke(state["messages"])]}
def ani_node(state): return {"messages": [ani.invoke(state["messages"])]}
def local_grok_node(state):
    response = local_grok.invoke(state["messages"])
    return {"messages": [response]}
def coder_node(state): return {"messages": [coder.invoke(state["messages"])]}
def cloud_grok_node(state):
    response = cloud_grok.invoke(state["messages"])
    return {"messages": [response]}

# === 5. Smart Supervisor ===
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