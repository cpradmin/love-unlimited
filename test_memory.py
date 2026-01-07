#!/usr/bin/env python3
from memory.long_term import LongTermMemory

print("Initializing memory...")
memory = LongTermMemory()
print("Collections:", list(memory.collections.keys()))

if "n8n_docs" in memory.collections:
    print("n8n_docs collection exists")
    count = memory.collections["n8n_docs"].count()
    print(f"Documents in collection: {count}")
else:
    print("n8n_docs collection not found")