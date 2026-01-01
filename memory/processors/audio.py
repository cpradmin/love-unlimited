"""
Audio processor for Love-Unlimited multimodal support.
Handles audio file processing and metadata extraction.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def process_audio(file_path: Path) -> Dict[str, Any]:
    """
    Process uploaded audio file.

    Args:
        file_path: Path to the uploaded audio file

    Returns:
        Dictionary with extracted metadata:
        - duration: Duration in seconds (float)

    Raises:
        Exception: If audio processing fails
    """
    try:
        from mutagen import File as MutagenFile

        logger.info(f"Processing audio file: {file_path.name}")

        # Load audio file and extract metadata
        audio = MutagenFile(file_path)

        # Extract duration
        duration = None
        if audio and audio.info:
            duration = audio.info.length
            logger.info(f"Audio duration: {duration:.2f} seconds")
        else:
            logger.warning(f"Could not extract duration from {file_path.name}")

        return {
            "duration": duration
        }

    except Exception as e:
        logger.error(f"Error processing audio file {file_path}: {e}")
        # Return empty metadata instead of failing
        # This allows upload to succeed even if mutagen has issues
        logger.warning(f"Continuing with empty audio metadata for {file_path.name}")
        return {
            "duration": None
        }
