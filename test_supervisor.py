from loveunlimited_supervisor import supervisor_chain
from langchain_core.messages import HumanMessage

# Test the supervisor with a sample query
test_messages = [HumanMessage(content="What are the latest developments in AI safety?")]

result = supervisor_chain.invoke({"messages": test_messages})
print("Supervisor routing decision:", result)