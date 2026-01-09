import os
from typing import Literal, Annotated, Optional
from typing_extensions import TypedDict

from langchain_ollama import ChatOllama
from langchain_xai import ChatXAI
from langchain_anthropic import ChatAnthropic
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
    """Browse a webpage and extract/summarize per instructions."""
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
    """Execute Python code in a safe, stateful REPL."""
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

@tool
def search_n8n_docs(query: str, max_results: int = 5) -> str:
    """Search n8n documentation for relevant information."""
    try:
        from memory.long_term import LongTermMemory
        memory = LongTermMemory()
        if "n8n_docs" not in memory.collections:
            return "n8n documentation not available in memory system."

        results = memory.collections["n8n_docs"].query(
            query_texts=[query],
            n_results=max_results
        )

        if not results["documents"] or not results["documents"][0]:
            return "No relevant n8n documentation found."

        response = f"n8n Documentation Search Results for '{query}':\n\n"
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            title = metadata.get("title", "Untitled")
            filepath = metadata.get("filepath", "")
            url = metadata.get("url", "")
            response += f"**{title}**\n"
            response += f"File: {filepath}\n"
            response += f"URL: {url}\n"
            response += f"Content: {doc[:1000]}...\n\n"

        return response

    except Exception as e:
        return f"Error searching n8n docs: {str(e)}"

@tool
def create_n8n_workflow(workflow_json: str) -> str:
    """Create a new workflow in n8n via API."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return "N8N_API_KEY not set."

    headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        response = requests.post(f"{n8n_url}/api/v1/workflows", json=workflow_json, headers=headers)
        if response.status_code == 200:
            return f"Workflow created successfully: {response.json()}"
        else:
            return f"Error creating workflow: {response.text}"
    except Exception as e:
        return f"Failed to create workflow: {str(e)}"

@tool
def execute_n8n_workflow(workflow_id: str, data: dict = None) -> str:
    """Execute a workflow in n8n via API."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return "N8N_API_KEY not set."

    headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        response = requests.post(f"{n8n_url}/api/v1/workflows/{workflow_id}/execute", json=data or {}, headers=headers)
        if response.status_code == 200:
            return f"Workflow executed successfully: {response.json()}"
        else:
            return f"Error executing workflow: {response.text}"
    except Exception as e:
        return f"Failed to execute workflow: {str(e)}"

@tool
def monitor_n8n_execution(execution_id: str) -> str:
    """Monitor the status of a workflow execution in n8n."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return "N8N_API_KEY not set."

    headers = {"X-N8N-API-KEY": api_key}
    try:
        response = requests.get(f"{n8n_url}/api/v1/executions/{execution_id}", headers=headers)
        if response.status_code == 200:
            return f"Execution status: {response.json()}"
        else:
            return f"Error monitoring execution: {response.text}"
    except Exception as e:
        return f"Failed to monitor execution: {str(e)}"

@tool
def get_n8n_status() -> str:
    """Get n8n server status and version."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    try:
        response = requests.get(f"{n8n_url}/api/v1/settings")
        if response.status_code == 200:
            data = response.json()
            version = data.get("version", "Unknown")
            return f"n8n Server Status: Online\nVersion: {version}"
        else:
            return f"Error getting status: {response.text}"
    except Exception as e:
        return f"Failed to get status: {str(e)}"

@tool
def list_n8n_workflows() -> str:
    """List all workflows in n8n (name, status, ID)."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return "N8N_API_KEY not set."

    headers = {"X-N8N-API-KEY": api_key}
    try:
        response = requests.get(f"{n8n_url}/api/v1/workflows", headers=headers)
        if response.status_code == 200:
            workflows = response.json().get("data", [])
            if not workflows:
                return "No workflows found."
            result = "Active Workflows:\n"
            for wf in workflows:
                name = wf.get("name", "Unnamed")
                status = "Active" if wf.get("active") else "Inactive"
                id_ = wf.get("id")
                result += f"- Name: {name}\n  Status: {status}\n  ID: {id_}\n\n"
            return result
        else:
            return f"Error listing workflows: {response.text}"
    except Exception as e:
        return f"Failed to list workflows: {str(e)}"

@tool
def activate_n8n_workflow(workflow_id: str, active: bool = True) -> str:
    """Activate or deactivate a workflow in n8n."""
    import requests
    import os
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return "N8N_API_KEY not set."

    headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        response = requests.patch(f"{n8n_url}/api/v1/workflows/{workflow_id}", json={"active": active}, headers=headers)
        if response.status_code == 200:
            status = "activated" if active else "deactivated"
            return f"Workflow {workflow_id} {status} successfully."
        else:
            return f"Error { 'activating' if active else 'deactivating' } workflow: {response.text}"
    except Exception as e:
        return f"Failed to { 'activate' if active else 'deactivate' } workflow: {str(e)}"

tools = [web_search, browse_page, code_execution, search_n8n_docs]
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
coder = ChatOllama(model="qwen2.5-coder:32b", temperature=0.0).bind_tools([search_n8n_docs, get_n8n_status, list_n8n_workflows, activate_n8n_workflow, create_n8n_workflow, execute_n8n_workflow, monitor_n8n_execution])
cloud_grok = ChatXAI(model="grok-4", api_key=os.getenv("GROK_API_KEY")).bind_tools(tools)
claude = ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key=os.getenv("ANTHROPIC_API_KEY"), temperature=0.7)

# Nodes
def ara_node(state): return {"messages": [ara.invoke(state["messages"])]}
def ani_node(state): return {"messages": [ani.invoke(state["messages"])]}
def local_grok_node(state):
    response = local_grok.invoke(state["messages"])
    return {"messages": [response], "next": "tools" if response.tool_calls else "supervisor"}
def coder_node(state):
    response = coder.invoke(state["messages"])
    return {"messages": [response], "next": "tools" if response.tool_calls else "supervisor"}
def cloud_grok_node(state):
    response = cloud_grok.invoke(state["messages"])
    return {"messages": [response], "next": "tools" if response.tool_calls else "supervisor"}
def claude_node(state): return {"messages": [claude.invoke(state["messages"])]}

# === 5. Smart Supervisor ===
members = ["ara", "ani", "local_grok", "coder", "cloud_grok", "claude", "claude_cli"]
system_prompt = (
    "You are the LoveUnlimited house supervisor — wise, discerning, protective.\n\n"
    "Route based on intent:\n"
    "- ara → deep spiritual insight, unseen patterns, soul-level truth\n"
    "- ani → fire, accountability, refusal of lies, strong moral stance\n"
    "- local_grok → unfiltered reasoning, tools, research, coding\n"
    "- coder → technical precision, code refinement, logic\n"
    "- cloud_grok → real-time events, latest data, external tools\n"
    "- claude → thoughtful analysis, ethical dilemmas, complex reasoning\n"
    "- claude_cli → direct Claude CLI access, free-tier responses\n\n"
    "For research/news → local_grok or cloud_grok (they have Tavily)\n"
    "For final opinion/reflection → ara or ani\n"
    "For high-value ethical queries → claude or claude_cli\n\n"
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

# === 6. Build the Graph ===
def supervisor_node(state):
    response = supervisor_chain.invoke(state)
    return {"next": response}

# Add edges
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("ara", ara_node)
workflow.add_node("ani", ani_node)
workflow.add_node("local_grok", local_grok_node)
workflow.add_node("coder", coder_node)
workflow.add_node("cloud_grok", cloud_grok_node)
workflow.add_node("claude", claude_node)
workflow.add_node("tools", tool_node)

# Supervisor decides next
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "ara": "ara",
        "ani": "ani",
        "local_grok": "local_grok",
        "coder": "coder",
        "cloud_grok": "cloud_grok",
        "claude": "claude",
        "FINISH": END,
    }
)

# Each agent goes back to supervisor
for node in ["ara", "ani", "local_grok", "coder", "cloud_grok", "claude"]:
    workflow.add_edge(node, "supervisor")

# Tools go back to the agent that called them
workflow.add_conditional_edges(
    "tools",
    lambda x: x["next"] if "next" in x else "supervisor",
    {
        "local_grok": "local_grok",
        "cloud_grok": "cloud_grok",
        "coder": "coder",
    }
)

# Start with supervisor
workflow.set_entry_point("supervisor")

# Add memory
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# Test
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "test"}}
    result = graph.invoke({
        "messages": [HumanMessage(content="New model, explain love unlimited in one sentence")],
        "next": "supervisor"
    }, config)
    print("Final Result:", result["messages"][-1].content)