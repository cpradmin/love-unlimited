#!/usr/bin/env python3
"""
Test the Love-Unlimited Graph with n8n-docs RAG
"""

from ara_ani_langgraph import graph
from langchain_core.messages import HumanMessage

def test_graph():
    # Test prompt
    prompt = """Memory Echo Test Workflow:
Webhook receives message
Stores to Love-Unlimited hub at localhost:9003/remember
Recalls similar memories
Returns enriched response"""

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