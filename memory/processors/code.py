"""
Code processor for Love-Unlimited multimodal support.
Handles code file processing, language detection, and text extraction.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Language mapping by file extension
EXT_TO_LANG = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.md': 'markdown',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.xml': 'xml',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',
    '.ps1': 'powershell',
    '.sql': 'sql',
    '.txt': 'text',
}


def process_code(file_path: Path) -> Dict[str, Any]:
    """
    Process uploaded code file.

    Args:
        file_path: Path to the uploaded code file

    Returns:
        Dictionary with extracted metadata:
        - language: Detected programming language
        - extracted_text: Full code content for semantic search

    Raises:
        Exception: If code processing fails
    """
    try:
        # Detect language from extension
        extension = file_path.suffix.lower()
        language = EXT_TO_LANG.get(extension, 'text')

        logger.info(f"Processing code file: {file_path.name} (language: {language})")

        # Read code content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            logger.warning(f"UTF-8 decode failed for {file_path.name}, trying latin-1")
            content = file_path.read_text(encoding='latin-1')

        logger.info(f"Extracted {len(content)} characters from {file_path.name}")

        return {
            "language": language,
            "extracted_text": content  # Store full content for semantic search
        }

    except Exception as e:
        logger.error(f"Error processing code file {file_path}: {e}")
        raise
