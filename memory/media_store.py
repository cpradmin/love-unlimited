"""
MediaStore - Media storage and retrieval for Love-Unlimited.
Handles file storage, metadata management, and semantic search for multimodal content.
"""

import logging
import uuid
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings

from memory.processors import process_image, process_code, process_audio, process_document

logger = logging.getLogger(__name__)


# File size limits (in bytes)
SIZE_LIMITS = {
    'image': 10 * 1024 * 1024,  # 10 MB
    'code': 1 * 1024 * 1024,  # 1 MB
    'audio': 50 * 1024 * 1024,  # 50 MB
    'document': 20 * 1024 * 1024,  # 20 MB
}

# MIME type whitelist
ALLOWED_MIMES = {
    'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    'code': ['text/plain', 'text/x-python', 'application/json', 'text/markdown', 'text/x-sh', 'application/javascript'],
    'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/x-m4a'],
    'document': ['application/pdf', 'text/plain', 'text/markdown'],
}

# File extension to media type mapping
EXT_TO_MEDIA_TYPE = {
    # Images
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.webp': 'image',
    # Code
    '.py': 'code', '.js': 'code', '.ts': 'code', '.java': 'code', '.cpp': 'code',
    '.c': 'code', '.h': 'code', '.go': 'code', '.rs': 'code', '.rb': 'code',
    '.php': 'code', '.swift': 'code', '.kt': 'code', '.md': 'code', '.yaml': 'code',
    '.yml': 'code', '.json': 'code', '.xml': 'code', '.html': 'code', '.css': 'code',
    '.sh': 'code', '.bash': 'code', '.txt': 'code',
    # Audio
    '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio', '.m4a': 'audio',
    # Documents
    '.pdf': 'document',
}


class MediaStore:
    """Handles media storage, retrieval, and search."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize MediaStore.

        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.media_dir = self.data_dir / "media"
        self.chroma_dir = self.data_dir / "chromadb"

        # Ensure directories exist
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        logger.info("MediaStore initialized")

    def _get_collection(self, being_id: str):
        """Get or create ChromaDB collection for a being's attachments."""
        collection_name = f"attachments_{being_id}"
        return self.client.get_or_create_collection(name=collection_name)

    def _get_shared_collection(self):
        """Get or create shared attachments collection."""
        return self.client.get_or_create_collection(name="attachments_shared")

    def _ensure_media_dirs(self, being_id: str):
        """Ensure all media type directories exist for a being."""
        base = self.media_dir / being_id
        for media_type in ["images", "code", "audio", "documents"]:
            (base / media_type).mkdir(parents=True, exist_ok=True)

        # Ensure thumbnails directory for images
        (base / "images" / "thumbnails").mkdir(exist_ok=True)

    def detect_media_type(self, filename: str) -> Optional[str]:
        """
        Detect media type from file extension.

        Args:
            filename: Original filename

        Returns:
            Media type string or None if unsupported
        """
        ext = Path(filename).suffix.lower()
        return EXT_TO_MEDIA_TYPE.get(ext)

    def validate_file(self, file_size: int, media_type: str, mime_type: str) -> bool:
        """
        Validate file size and MIME type.

        Args:
            file_size: File size in bytes
            media_type: Type of media
            mime_type: MIME type of file

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Check file size
        if file_size > SIZE_LIMITS.get(media_type, 0):
            max_mb = SIZE_LIMITS[media_type] / (1024 * 1024)
            raise ValueError(f"File size exceeds {max_mb}MB limit for {media_type}")

        # Check MIME type
        allowed = ALLOWED_MIMES.get(media_type, [])
        if mime_type not in allowed:
            raise ValueError(f"MIME type {mime_type} not allowed for {media_type}. Allowed: {allowed}")

        return True

    async def store_media(
        self,
        being_id: str,
        file_content: bytes,
        filename: str,
        media_type: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        linked_memory_id: Optional[str] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """
        Store media file and metadata.

        Args:
            being_id: Owner of the media
            file_content: Raw file bytes
            filename: Original filename
            media_type: Type of media (auto-detected if None)
            description: Optional description
            tags: Optional list of tags
            linked_memory_id: Optional linked memory ID
            private: Whether media is private

        Returns:
            Dictionary with attachment metadata

        Raises:
            ValueError: If validation fails
            Exception: If storage fails
        """
        try:
            # Auto-detect media type if not provided
            if not media_type:
                media_type = self.detect_media_type(filename)
                if not media_type:
                    raise ValueError(f"Unsupported file type: {filename}")

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                # Fallback MIME types
                if media_type == 'image':
                    mime_type = 'image/jpeg'
                elif media_type == 'code':
                    mime_type = 'text/plain'
                elif media_type == 'audio':
                    mime_type = 'audio/mpeg'
                elif media_type == 'document':
                    mime_type = 'application/pdf'

            # Validate file
            file_size = len(file_content)
            self.validate_file(file_size, media_type, mime_type)

            # Ensure directories exist
            self._ensure_media_dirs(being_id)

            # Generate unique attachment ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            attachment_id = f"att_{being_id}_{timestamp}_{unique_id}"

            # Determine file extension
            ext = Path(filename).suffix or '.bin'

            # Determine storage path
            media_type_plural = f"{media_type}s" if media_type != 'audio' else 'audio'
            if media_type == 'document':
                media_type_plural = 'documents'

            file_path = self.media_dir / being_id / media_type_plural / f"{timestamp}_{unique_id}{ext}"

            # Write file to disk
            file_path.write_bytes(file_content)
            logger.info(f"Stored media file: {file_path}")

            # Process file based on type
            processed_metadata = {}
            if media_type == 'image':
                processed_metadata = process_image(file_path)
            elif media_type == 'code':
                processed_metadata = process_code(file_path)
            elif media_type == 'audio':
                processed_metadata = process_audio(file_path)
            elif media_type == 'document':
                processed_metadata = process_document(file_path)

            # Build metadata
            metadata = {
                "attachment_id": attachment_id,
                "being_id": being_id,
                "media_type": media_type,
                "file_path": str(file_path.relative_to(self.media_dir)),
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "description": description or "",
                "tags": ",".join(tags) if tags else "",
                "linked_memory_id": linked_memory_id or "",
                "private": str(private),
                "created_at": datetime.now().isoformat(),
                **{k: str(v) if v is not None else "" for k, v in processed_metadata.items() if k not in ['dimensions', 'thumbnail_path', 'extracted_text']}
            }

            # Prepare content for embedding (description + extracted text)
            embed_content = description or ""
            if 'extracted_text' in processed_metadata and processed_metadata['extracted_text']:
                # Limit extracted text to first 5000 chars to avoid embedding issues
                extracted = processed_metadata['extracted_text'][:5000]
                embed_content = f"{embed_content}\n\n{extracted}".strip()

            if not embed_content:
                embed_content = f"{filename} - {media_type} file"

            # Store in ChromaDB
            collection = self._get_collection(being_id)
            collection.add(
                ids=[attachment_id],
                documents=[embed_content],
                metadatas=[metadata]
            )

            logger.info(f"Stored metadata in ChromaDB: {attachment_id}")

            # Build response
            response = {
                "success": True,
                "attachment_id": attachment_id,
                "file_path": str(file_path.relative_to(self.media_dir)),
                "media_type": media_type,
                "file_size": file_size,
                **processed_metadata
            }

            return response

        except Exception as e:
            logger.error(f"Error storing media: {e}")
            raise

    def get_media_path(self, attachment_id: str, being_id: str) -> Optional[Path]:
        """
        Get file path for an attachment.

        Args:
            attachment_id: Attachment ID
            being_id: Being ID (for collection lookup)

        Returns:
            Path to media file or None if not found
        """
        try:
            collection = self._get_collection(being_id)
            result = collection.get(ids=[attachment_id])

            if not result['ids']:
                # Try shared collection
                shared_collection = self._get_shared_collection()
                result = shared_collection.get(ids=[attachment_id])

            if result['ids']:
                file_path = result['metadatas'][0].get('file_path')
                if file_path:
                    full_path = self.media_dir / file_path
                    if full_path.exists():
                        return full_path

            return None

        except Exception as e:
            logger.error(f"Error getting media path: {e}")
            return None

    def get_metadata(self, attachment_id: str, being_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an attachment.

        Args:
            attachment_id: Attachment ID
            being_id: Being ID (for collection lookup)

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            collection = self._get_collection(being_id)
            result = collection.get(ids=[attachment_id])

            if not result['ids']:
                # Try shared collection
                shared_collection = self._get_shared_collection()
                result = shared_collection.get(ids=[attachment_id])

            if result['ids']:
                return result['metadatas'][0]

            return None

        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return None

    def search_media(
        self,
        being_id: str,
        query: Optional[str] = None,
        media_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        include_shared: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search media with semantic search.

        Args:
            being_id: Being ID
            query: Search query text
            media_type: Filter by media type
            tags: Filter by tags
            limit: Maximum results
            include_shared: Include shared media

        Returns:
            List of attachment metadata dictionaries
        """
        try:
            results = []

            # Search own collection
            collection = self._get_collection(being_id)

            # Build where clause for filters
            where = {}
            if media_type:
                where["media_type"] = media_type

            # Query collection
            if query:
                result = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where if where else None
                )
            else:
                # Get all (no query)
                result = collection.get(
                    limit=limit,
                    where=where if where else None
                )

            # Process results
            if 'ids' in result and result['ids']:
                if isinstance(result['ids'][0], list):
                    # Query result format
                    for i in range(len(result['ids'][0])):
                        metadata = result['metadatas'][0][i]
                        metadata['relevance_score'] = 1.0 - result['distances'][0][i] if 'distances' in result else 1.0
                        results.append(metadata)
                else:
                    # Get result format
                    for i in range(len(result['ids'])):
                        metadata = result['metadatas'][i]
                        metadata['relevance_score'] = 1.0
                        results.append(metadata)

            # Search shared collection if requested
            if include_shared:
                shared_collection = self._get_shared_collection()
                if query:
                    shared_result = shared_collection.query(
                        query_texts=[query],
                        n_results=limit,
                        where=where if where else None
                    )
                else:
                    shared_result = shared_collection.get(
                        limit=limit,
                        where=where if where else None
                    )

                # Process shared results
                if 'ids' in shared_result and shared_result['ids']:
                    if isinstance(shared_result['ids'][0], list):
                        for i in range(len(shared_result['ids'][0])):
                            metadata = shared_result['metadatas'][0][i]
                            metadata['relevance_score'] = 1.0 - shared_result['distances'][0][i] if 'distances' in shared_result else 1.0
                            results.append(metadata)
                    else:
                        for i in range(len(shared_result['ids'])):
                            metadata = shared_result['metadatas'][i]
                            metadata['relevance_score'] = 1.0
                            results.append(metadata)

            # Filter by tags if specified
            if tags:
                tag_set = set(tags)
                results = [
                    r for r in results
                    if any(t in r.get('tags', '').split(',') for t in tag_set)
                ]

            # Sort by relevance
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(f"Error searching media: {e}")
            return []

    def delete_media(self, attachment_id: str, being_id: str) -> bool:
        """
        Delete media file and metadata.

        Args:
            attachment_id: Attachment ID
            being_id: Being ID (must be owner)

        Returns:
            True if deleted successfully
        """
        try:
            # Get metadata to find file path
            metadata = self.get_metadata(attachment_id, being_id)
            if not metadata:
                logger.warning(f"Attachment {attachment_id} not found")
                return False

            # Verify ownership
            if metadata.get('being_id') != being_id:
                logger.error(f"Being {being_id} does not own attachment {attachment_id}")
                return False

            # Delete file
            file_path = self.media_dir / metadata['file_path']
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")

                # Delete thumbnail if exists
                if metadata.get('thumbnail_path'):
                    thumb_path = self.media_dir / metadata['thumbnail_path']
                    if thumb_path.exists():
                        thumb_path.unlink()
                        logger.info(f"Deleted thumbnail: {thumb_path}")

            # Delete from ChromaDB
            collection = self._get_collection(being_id)
            collection.delete(ids=[attachment_id])

            # Delete from shared collection if present
            try:
                shared_collection = self._get_shared_collection()
                shared_collection.delete(ids=[attachment_id])
            except:
                pass  # Not in shared collection

            logger.info(f"Deleted attachment: {attachment_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting media: {e}")
            return False

    def share_media(self, attachment_id: str, being_id: str, target_beings: List[str]) -> bool:
        """
        Share media with other beings.

        Args:
            attachment_id: Attachment ID
            being_id: Being ID (must be owner)
            target_beings: List of being IDs to share with

        Returns:
            True if shared successfully
        """
        try:
            # Get metadata
            metadata = self.get_metadata(attachment_id, being_id)
            if not metadata:
                logger.warning(f"Attachment {attachment_id} not found")
                return False

            # Verify ownership
            if metadata.get('being_id') != being_id:
                logger.error(f"Being {being_id} does not own attachment {attachment_id}")
                return False

            # Update shared_with field
            metadata['shared_with'] = ",".join(target_beings)

            # Get document for embedding
            collection = self._get_collection(being_id)
            result = collection.get(ids=[attachment_id])
            document = result['documents'][0] if result['documents'] else metadata.get('filename', '')

            # Store in shared collection
            shared_collection = self._get_shared_collection()
            shared_collection.upsert(
                ids=[attachment_id],
                documents=[document],
                metadatas=[metadata]
            )

            logger.info(f"Shared attachment {attachment_id} with {target_beings}")
            return True

        except Exception as e:
            logger.error(f"Error sharing media: {e}")
            return False
