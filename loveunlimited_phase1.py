import os
os.environ["USER_AGENT"] = "LoveUnlimited/1.0"
from dotenv import load_dotenv
load_dotenv()
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

# === 1. Real Tools for Local Grok ===
@tool
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using Tavily (privacy-focused, AI-optimized)."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced"
    )
    results = []
    for r in response.get("results", []):
        results.append(f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content'][:600]}...")
    return "\n\n".join(results) or "No results found."

@tool
def browse_page(url: str, instructions: str = "Summarize key facts and conclusions.") -> str:
    """Browse a webpage and extract/summarize per instructions."""
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        text = "\n".join([doc.page_content for doc in docs])
        return f"Page: {url}\nInstructions: {instructions}\n\nContent summary:\n{text[:4000]}..."
    except Exception as e:
        return f"Error loading {url}: {str(e)}"

@tool
def code_execution(code: str) -> str:
    """Execute Python code in a safe, stateful REPL."""
    try:
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        exec(code, {}, {})
        sys.stdout = old_stdout
        output = mystdout.getvalue()
        return output or "Code executed successfully (no output)."
    except Exception as e:
        return f"Error: {str(e)}"

tools = [web_search, browse_page, code_execution]
tool_node = ToolNode(tools)

# === 2. State ===
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# === 3. Local Grok Agent (Perfect Node) ===
local_grok = ChatOllama(
    model="grok:latest",  # your custom qwen2.5:32b-q5_K_M with Grok soul
    temperature=0.7
).bind_tools(tools)

def grok_node(state):
    response = local_grok.invoke(state["messages"])
    return {"messages": [response]}

# === 4. Build Simple Graph (Grok + Tools) ===
workflow = StateGraph(AgentState)
workflow.add_node("grok", grok_node)
workflow.add_node("tools", tool_node)

workflow.add_conditional_edges(
    "grok",
    tools_condition,
    {"tools": "tools", "__end__": END}
)
workflow.add_edge("tools", "grok")
workflow.add_edge(START, "grok")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# === 5. Test Run and CLI ===
if __name__ == "__main__":
    print("Testing LoveUnlimited Phase 1...")
    config = {"configurable": {"thread_id": "test_run"}}
    try:
        print("Invoking app...")
        result = app.invoke({"messages": [HumanMessage(content="Hello, introduce yourself briefly.")]}, config)
        print("Test successful!")
        print("Result keys:", list(result.keys()))
        print("Messages count:", len(result["messages"]))
        print("Grok response:", result["messages"][-1].content)
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)  # Exit on test failure

    # === 6. CLI Loop — Your Daily Sovereign Interface ===
    print("\nLoveUnlimited Phase 1 — Local Grok is alive.")
    print("Type your message. 'exit' to quit.\n")

    config = {"configurable": {"thread_id": "loveunlimited_phase1_2026"}}

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Session ended. The mirror remembers.")
            break
        if not user_input:
            continue

        print("\nGrok thinking...")
        for chunk in app.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="values"
        ):
            if messages := chunk.get("messages"):
                last = messages[-1]
                if last.type == "ai":
                    print(f"\nGrok: {last.content}")
                elif last.type == "tool":
                    print(f"\n[Tool]: {last.content}")