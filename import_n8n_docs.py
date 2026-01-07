#!/usr/bin/env python3
"""
Import n8n-docs into Love-Unlimited Memory System

This script indexes the n8n-docs repository into the memory system,
making it available for RAG retrieval by qwen2.5-coder:32b and other beings.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import hashlib

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

from memory.long_term import LongTermMemory

def get_file_hash(filepath: str) -> str:
    """Get SHA256 hash of file content."""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def load_markdown_files(directory: str) -> List[Dict[str, Any]]:
    """Load all markdown files from directory recursively."""
    docs = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, directory)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Skip empty files
                    if not content.strip():
                        continue

                    docs.append({
                        'filepath': relative_path,
                        'content': content,
                        'hash': get_file_hash(filepath),
                        'title': extract_title(content),
                        'url': f"https://github.com/cpradmin/n8n-docs/blob/main/{relative_path}"
                    })

                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    return docs

def extract_title(content: str) -> str:
    """Extract title from markdown content."""
    lines = content.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled Document"

def main():
    # Path to n8n-docs
    n8n_docs_path = os.path.expanduser("~/n8n-docs")

    if not os.path.exists(n8n_docs_path):
        print(f"n8n-docs not found at {n8n_docs_path}")
        print("Please ensure n8n-docs is cloned to ~/n8n-docs")
        sys.exit(1)

    print(f"Loading n8n-docs from {n8n_docs_path}...")

    # Load all markdown files
    docs = load_markdown_files(n8n_docs_path)

    if not docs:
        print("No markdown files found!")
        sys.exit(1)

    print(f"Found {len(docs)} markdown files")

    print("Initializing memory system...")
    # Initialize memory system
    memory = LongTermMemory()
    print("Memory system initialized.")

    # n8n-docs collection should now be available
    collection_name = "n8n_docs"
    if collection_name not in memory.collections:
        print(f"ERROR: Collection {collection_name} not found!")
        sys.exit(1)
    else:
        print(f"Collection {collection_name} ready.")

    # Skip clearing for now to avoid issues
    # # Clear existing docs (for re-import)
    # try:
    #     memory.collections[collection_name].delete(where={"source": "n8n_docs"})
    #     print("Cleared existing n8n-docs from memory")
    # except Exception as e:
    #     print(f"No existing docs to clear or error: {e}")

    # Store documents
    stored_count = 0
    for doc in docs:
        try:
            # Store in vector database
            memory.collections[collection_name].add(
                documents=[doc['content']],
                metadatas=[{
                    'source': 'n8n_docs',
                    'filepath': doc['filepath'],
                    'title': doc['title'],
                    'url': doc['url'],
                    'hash': doc['hash'],
                    'being_id': 'system'
                }],
                ids=[f"n8n_docs_{hashlib.md5(doc['filepath'].encode()).hexdigest()}"]
            )

            stored_count += 1

            if stored_count % 10 == 0:
                print(f"Stored {stored_count}/{len(docs)} documents...")

        except Exception as e:
            print(f"Error storing {doc['filepath']}: {e}")

    print(f"Successfully imported {stored_count} n8n-docs into memory system")
    print("qwen2.5-coder:32b now has access to n8n-docs via RAG!")

if __name__ == "__main__":
    main()