"""
Document processor for Love-Unlimited multimodal support.
Handles PDF, Markdown, and text document processing.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def process_document(file_path: Path) -> Dict[str, Any]:
    """
    Process uploaded document file.

    Args:
        file_path: Path to the uploaded document file

    Returns:
        Dictionary with extracted metadata:
        - extracted_text: Full text content for semantic search
        - page_count: Number of pages (PDF only)

    Raises:
        Exception: If document processing fails
    """
    try:
        extension = file_path.suffix.lower()

        logger.info(f"Processing document: {file_path.name} (type: {extension})")

        if extension == '.pdf':
            return _process_pdf(file_path)
        elif extension in ['.md', '.txt']:
            return _process_text(file_path)
        else:
            logger.warning(f"Unsupported document type: {extension}")
            return {"extracted_text": ""}

    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        raise


def _process_pdf(file_path: Path) -> Dict[str, Any]:
    """Process PDF file and extract text."""
    from PyPDF2 import PdfReader

    logger.info(f"Extracting text from PDF: {file_path.name}")

    reader = PdfReader(file_path)
    page_count = len(reader.pages)

    # Extract text from all pages
    text_parts = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        except Exception as e:
            logger.warning(f"Error extracting text from page {i+1}: {e}")

    extracted_text = "\n".join(text_parts)

    logger.info(f"Extracted {len(extracted_text)} characters from {page_count} pages")

    return {
        "page_count": page_count,
        "extracted_text": extracted_text
    }


def _process_text(file_path: Path) -> Dict[str, Any]:
    """Process plain text or markdown file."""
    try:
        text = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try with latin-1 encoding as fallback
        logger.warning(f"UTF-8 decode failed for {file_path.name}, trying latin-1")
        text = file_path.read_text(encoding='latin-1')

    logger.info(f"Extracted {len(text)} characters from {file_path.name}")

    return {
        "extracted_text": text
    }
