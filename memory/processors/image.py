"""
Image processor for Love-Unlimited multimodal support.
Handles image upload processing, thumbnail generation, and metadata extraction.
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def process_image(file_path: Path) -> Dict[str, Any]:
    """
    Process uploaded image file.

    Args:
        file_path: Path to the uploaded image file

    Returns:
        Dictionary with extracted metadata:
        - dimensions: {width, height}
        - thumbnail_path: Path to generated thumbnail

    Raises:
        Exception: If image processing fails
    """
    try:
        from PIL import Image

        # Open image and get dimensions
        img = Image.open(file_path)
        width, height = img.size

        logger.info(f"Processing image: {file_path.name} ({width}x{height})")

        # Generate thumbnail (256x256)
        thumb = img.copy()
        thumb.thumbnail((256, 256))

        # Ensure thumbnails directory exists
        thumb_dir = file_path.parent / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        # Save thumbnail
        thumb_path = thumb_dir / f"{file_path.stem}_thumb.jpg"
        thumb.save(thumb_path, "JPEG", quality=85)

        logger.info(f"Generated thumbnail: {thumb_path}")

        return {
            "dimensions": {"width": width, "height": height},
            "thumbnail_path": str(thumb_path.relative_to(file_path.parents[2]))  # Relative to data/media/
        }

    except Exception as e:
        logger.error(f"Error processing image {file_path}: {e}")
        raise
