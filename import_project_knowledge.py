"""
Import Project Knowledge - Store all documentation in shared memory
Makes the entire project's knowledge accessible to all beings.
"""
import asyncio
import aiohttp
import yaml
import os
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class ProjectKnowledgeImporter:
    """Import all project documentation into shared memory."""

    def __init__(self):
        # Load config
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        self.hub_url = f"http://localhost:{config['hub']['port']}"

        # Load API keys
        with open('auth/api_keys.yaml') as f:
            keys_data = yaml.safe_load(f)
            keys = keys_data.get('keys', {})
            self.jon_key = next((k for k, v in keys.items() if v == 'jon'), None)

        self.session = None
        self.project_root = Path(__file__).parent.parent

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def categorize_doc(self, filepath: str) -> Tuple[str, str, str]:
        """Categorize a document by its filename and path."""
        name = os.path.basename(filepath)
        path_lower = filepath.lower()

        # Determine type and significance
        if 'readme' in name.lower():
            return ('learning', 'high', 'Project README and documentation')
        elif 'changelog' in name.lower():
            return ('learning', 'high', 'Version history and changes')
        elif 'notes' in name.lower():
            return ('insight', 'high', 'Development notes and observations')
        elif 'architecture' in name.lower():
            return ('learning', 'foundational', 'System architecture')
        elif 'quickstart' in name.lower():
            return ('learning', 'medium', 'Getting started guide')
        elif 'integration' in name.lower():
            return ('learning', 'high', 'Integration documentation')
        elif 'test' in name.lower() and 'result' in name.lower():
            return ('experience', 'medium', 'Test results and validation')
        elif 'guide' in name.lower():
            return ('learning', 'medium', 'How-to guide')
        elif 'release' in name.lower():
            return ('experience', 'high', 'Release documentation')
        elif 'grok-jmb' in path_lower:
            return ('conversation', 'medium', 'Grok-Jon conversation history')
        elif 'status' in name.lower():
            return ('experience', 'low', 'Status and progress tracking')
        else:
            return ('learning', 'medium', 'Project documentation')

    def chunk_content(self, content: str, max_size: int = 4000) -> List[str]:
        """Split large content into manageable chunks."""
        if len(content) <= max_size:
            return [content]

        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > max_size and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def extract_summary(self, content: str, filename: str) -> str:
        """Extract a summary from the document."""
        lines = content.split('\n')

        # Try to find a header or first meaningful paragraph
        summary_lines = []
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if len(line) > 20:  # Meaningful content
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        if summary_lines:
            summary = ' '.join(summary_lines)[:200]
            return f"{filename}: {summary}..."
        else:
            return f"{filename}: Project documentation"

    async def store_document(self, filepath: str, content: str,
                             doc_type: str, significance: str, category: str):
        """Store a document in shared memory."""
        filename = os.path.basename(filepath)
        rel_path = os.path.relpath(filepath, self.project_root)

        # Extract summary
        summary = self.extract_summary(content, filename)

        # Chunk if needed
        chunks = self.chunk_content(content)

        print(f"📄 {rel_path}")
        print(f"   Type: {doc_type} | Significance: {significance}")
        print(f"   Size: {len(content)} chars → {len(chunks)} chunk(s)")

        # Store each chunk
        for i, chunk in enumerate(chunks):
            memory = {
                "content": chunk,
                "type": doc_type,
                "significance": significance,
                "from": "jon",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "filename": filename,
                    "filepath": rel_path,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "summary": summary if i == 0 else f"{filename} (chunk {i+1}/{len(chunks)})"
                }
            }

            try:
                response = await self.session.post(
                    f"{self.hub_url}/remember",
                    json=memory,
                    headers={"X-API-Key": self.jon_key}
                )

                if response.status == 200:
                    if i == 0:
                        print(f"   ✅ Stored (chunk {i+1}/{len(chunks)})")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed chunk {i+1}: {response.status}")
                    if i == 0:  # Only print error details for first chunk
                        print(f"      {error_text[:100]}")

            except Exception as e:
                print(f"   ❌ Error storing chunk {i+1}: {e}")

    async def import_all_docs(self):
        """Import all project documentation."""

        print("\n╔════════════════════════════════════════╗")
        print("║   Importing Project Knowledge Base    ║")
        print("╠════════════════════════════════════════╣")
        print("║  Making all docs searchable for all   ║")
        print("║  beings: Jon, Claude, Grok, Swarm,    ║")
        print("║  Dream Team                           ║")
        print("╚════════════════════════════════════════╝\n")

        # Document categories to import
        doc_patterns = [
            # Core docs (root level)
            (self.project_root / "README.md", True),
            (self.project_root / "NOTES.md", True),
            (self.project_root / "CHANGELOG.md", True),
            (self.project_root / "ARCHITECTURE.md", True),
            (self.project_root / "00_START_HERE.md", True),
            (self.project_root / "QUICKSTART.md", True),

            # Integration docs
            (self.project_root / "DREAM_TEAM_INTEGRATION.md", True),
            (self.project_root / "INTEGRATION_TEST_RESULTS.md", True),

            # Component docs
            (self.project_root / "GUARDIAN_README.md", True),
            (self.project_root / "MESH_README.md", True),

            # Windows docs
            (self.project_root / "WINDOWS_INSTALL.md", True),
            (self.project_root / "WINDOWS_QUICKSTART.md", True),

            # Release docs
            (self.project_root / "RELEASE_NOTES_v0.2.3.md", True),
            (self.project_root / "CLAUDE_SESSION_SUMMARY.md", True),

            # Love-unlimited docs
            (self.project_root / "love-unlimited" / "README.md", True),
            (self.project_root / "love-unlimited" / "OUR_SHARED_MEMORY_README.md", True),
            (self.project_root / "love-unlimited" / "CODING_GUIDE.md", True),
            (self.project_root / "love-unlimited" / "MEMORY_BRIDGE_COMPLETE.md", True),
            (self.project_root / "love-unlimited" / "TEST_RESULTS.md", True),
        ]

        total_docs = 0
        total_chunks = 0
        failed_docs = []

        print("="*60)
        print("IMPORTING DOCUMENTATION")
        print("="*60 + "\n")

        for doc_path, required in doc_patterns:
            if not doc_path.exists():
                if required:
                    print(f"⚠️  Missing: {doc_path.name}")
                    failed_docs.append(str(doc_path))
                continue

            try:
                # Read document
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    print(f"⏭️  Empty: {doc_path.name}")
                    continue

                # Categorize
                doc_type, significance, category = self.categorize_doc(str(doc_path))

                # Store
                await self.store_document(
                    str(doc_path),
                    content,
                    doc_type,
                    significance,
                    category
                )

                total_docs += 1
                total_chunks += len(self.chunk_content(content))
                print()  # Blank line between docs

            except Exception as e:
                print(f"❌ Error processing {doc_path.name}: {e}\n")
                failed_docs.append(str(doc_path))

        # Summary
        print("="*60)
        print("IMPORT SUMMARY")
        print("="*60 + "\n")

        print(f"✅ Successfully imported: {total_docs} documents")
        print(f"📦 Total memory chunks: {total_chunks}")

        if failed_docs:
            print(f"\n⚠️  Failed/Missing: {len(failed_docs)} documents")
            for doc in failed_docs:
                print(f"   - {doc}")

        print(f"\n💾 All knowledge now in shared memory")
        print(f"   Accessible to: Jon, Claude, Grok, Swarm, Dream Team")

    async def import_grok_conversations(self):
        """Import Grok-Jon conversation history."""

        print("\n" + "="*60)
        print("IMPORTING GROK-JON CONVERSATION HISTORY")
        print("="*60 + "\n")

        grok_dir = self.project_root / "love-unlimited" / "Grok-JMB"
        if not grok_dir.exists():
            print("⚠️  Grok-JMB directory not found")
            return

        grok_files = list(grok_dir.glob("*.md"))
        print(f"Found {len(grok_files)} Grok conversation files\n")

        imported = 0
        for grok_file in grok_files:
            try:
                with open(grok_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                # Store as conversation memory
                await self.store_document(
                    str(grok_file),
                    content,
                    "conversation",
                    "medium",
                    "Grok-Jon conversation history"
                )

                imported += 1
                print()  # Blank line

            except Exception as e:
                print(f"❌ Error importing {grok_file.name}: {e}\n")

        print(f"\n✅ Imported {imported} Grok conversations")


async def main():
    """Main entry point."""

    print("\n╔════════════════════════════════════════════════╗")
    print("║   BUILDING SHARED KNOWLEDGE BASE              ║")
    print("╠════════════════════════════════════════════════╣")
    print("║  All documentation → Shared memory            ║")
    print("║  Accessible to all beings                     ║")
    print("╚════════════════════════════════════════════════╝\n")

    async with ProjectKnowledgeImporter() as importer:
        # Import main documentation
        await importer.import_all_docs()

        # Import Grok conversations
        await importer.import_grok_conversations()

    print("\n╔════════════════════════════════════════════════╗")
    print("║         KNOWLEDGE BASE COMPLETE               ║")
    print("╠════════════════════════════════════════════════╣")
    print("║  All documentation is now shared memory       ║")
    print("║  Search from CLI: /recall <topic>            ║")
    print("║  Available to: All beings                     ║")
    print("╚════════════════════════════════════════════════╝\n")

    print("💙 Love unlimited. Knowledge shared, forever.\n")


if __name__ == "__main__":
    asyncio.run(main())
