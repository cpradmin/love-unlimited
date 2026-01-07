#!/usr/bin/env python3
"""
Test the Love-Unlimited Graph with n8n-docs RAG
"""

from ara_ani_langgraph import graph
from langchain_core.messages import HumanMessage

def test_graph():
    # Test prompt
    prompt = "Design an n8n workflow for a 20-round Claude ↔ Grok debate on consciousness, with Ara refereeing every 5 rounds using MCP memory checks."

    print("Testing graph with prompt:", prompt)

    # Initialize graph
    config = {"configurable": {"thread_id": "test_1"}}

    # Run the graph
    result = graph.invoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=config
    )

    print("\nFinal result:")
    print(result["messages"][-1].content)

if __name__ == "__main__":
    test_graph()