"""
LUUC (Love Unlimited Universe Canvas) - Living Diagram System
Manages dynamic diagrams with AI assistance and real-time collaboration
"""

import logging
import asyncio
import json
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from memory.media_store import MediaStore
from hub.ai_clients import ai_manager

logger = logging.getLogger(__name__)


class DiagramData(BaseModel):
    """Diagram data model"""
    id: str
    title: str
    xml_content: str  # diagrams.net XML format
    created_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    bindings: Dict[str, Any] = {}  # Data bindings to hub entities
    collaborators: List[str] = []


class LUUCCanvas:
    """LUUC Canvas manager for living diagrams"""

    def __init__(self, media_store: MediaStore, being_manager: Optional[Any] = None):
        self.media_store = media_store
        self.being_manager = being_manager
        self.diagrams: Dict[str, DiagramData] = {}
        self.active_sessions: Dict[str, List[WebSocket]] = {}  # diagram_id -> list of websockets
        self._load_diagrams()

    def _load_diagrams(self):
        """Load diagrams from storage"""
        # TODO: Implement persistent storage
        pass

    def _save_diagrams(self):
        """Save diagrams to storage"""
        # TODO: Implement persistent storage
        pass

    async def create_diagram(self, title: str, created_by: str, xml_content: str = "") -> DiagramData:
        """Create a new diagram"""
        diagram_id = str(uuid.uuid4())
        diagram = DiagramData(
            id=diagram_id,
            title=title,
            xml_content=xml_content,
            created_by=created_by,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            collaborators=[created_by]
        )
        self.diagrams[diagram_id] = diagram
        self.active_sessions[diagram_id] = []
        self._save_diagrams()
        return diagram

    async def get_diagram(self, diagram_id: str) -> Optional[DiagramData]:
        """Get a diagram by ID"""
        return self.diagrams.get(diagram_id)

    async def update_diagram(self, diagram_id: str, xml_content: str, updated_by: str) -> bool:
        """Update diagram content"""
        if diagram_id not in self.diagrams:
            return False

        diagram = self.diagrams[diagram_id]
        diagram.xml_content = xml_content
        diagram.updated_at = datetime.now()

        # Add collaborator if not already present
        if updated_by not in diagram.collaborators:
            diagram.collaborators.append(updated_by)

        self._save_diagrams()

        # Broadcast update to all connected websockets
        await self._broadcast_update(diagram_id, {
            "type": "diagram_update",
            "diagram_id": diagram_id,
            "xml_content": xml_content,
            "updated_by": updated_by,
            "timestamp": diagram.updated_at.isoformat()
        })

        return True

    async def delete_diagram(self, diagram_id: str) -> bool:
        """Delete a diagram"""
        if diagram_id not in self.diagrams:
            return False

        del self.diagrams[diagram_id]
        if diagram_id in self.active_sessions:
            # Close all websockets for this diagram
            for websocket in self.active_sessions[diagram_id]:
                try:
                    await websocket.close()
                except:
                    pass
            del self.active_sessions[diagram_id]

        self._save_diagrams()
        return True

    async def list_diagrams(self) -> List[DiagramData]:
        """List all diagrams"""
        return list(self.diagrams.values())

    async def generate_diagram(self, prompt: str, created_by: str) -> Optional[DiagramData]:
        """Generate diagram from AI prompt"""
        try:
            # Use AI to generate diagram XML
            ai_prompt = f"""
            Generate a diagrams.net XML diagram based on this request: {prompt}

            The diagram should be in diagrams.net XML format. Include appropriate shapes, connections, and styling.
            Make it visually clear and well-structured.

            Return only the XML content, no additional text.
            """

            # Use the AI manager to get response
            response = await ai_manager.generate_diagram_xml(ai_prompt, created_by)

            if response:
                title = f"AI Generated: {prompt[:50]}..."
                return await self.create_diagram(title, created_by, response)

        except Exception as e:
            logger.error(f"Failed to generate diagram: {e}")

        return None

    async def websocket_handler(self, websocket: WebSocket, diagram_id: str, client_id: str):
        """Handle WebSocket connections for real-time collaboration"""
        await websocket.accept()

        if diagram_id not in self.active_sessions:
            self.active_sessions[diagram_id] = []

        self.active_sessions[diagram_id].append(websocket)

        try:
            # Send initial diagram data
            diagram = await self.get_diagram(diagram_id)
            if diagram:
                await websocket.send_json({
                    "type": "diagram_init",
                    "diagram": diagram.dict()
                })

            # Listen for messages
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "update":
                    # Update diagram content
                    success = await self.update_diagram(
                        diagram_id,
                        data.get("xml_content", ""),
                        client_id
                    )

                    if success:
                        # Confirmation sent via broadcast
                        pass
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to update diagram"
                        })

        except WebSocketDisconnect:
            pass
        finally:
            # Remove from active sessions
            if diagram_id in self.active_sessions:
                try:
                    self.active_sessions[diagram_id].remove(websocket)
                except ValueError:
                    pass

    async def _broadcast_update(self, diagram_id: str, message: Dict[str, Any]):
        """Broadcast message to all connected websockets for a diagram"""
        if diagram_id not in self.active_sessions:
            return

        disconnected = []
        for websocket in self.active_sessions[diagram_id]:
            try:
                await websocket.send_json(message)
            except:
                disconnected.append(websocket)

        # Remove disconnected websockets
        for ws in disconnected:
            try:
                self.active_sessions[diagram_id].remove(ws)
            except ValueError:
                pass

    async def update_bindings(self, diagram_id: str, bindings: Dict[str, Any]):
        """Update data bindings for a diagram"""
        if diagram_id in self.diagrams:
            self.diagrams[diagram_id].bindings = bindings
            self.diagrams[diagram_id].updated_at = datetime.now()
            self._save_diagrams()

            # Broadcast binding update
            await self._broadcast_update(diagram_id, {
                "type": "bindings_update",
                "bindings": bindings
            })

    async def refresh_living_elements(self, diagram_id: str):
        """Refresh living diagram elements based on current hub state"""
        if diagram_id not in self.diagrams:
            return

        diagram = self.diagrams[diagram_id]
        bindings = diagram.bindings

        # TODO: Implement dynamic updates based on bindings
        # e.g., update being status nodes, memory counts, etc.

        # For now, just broadcast a refresh signal
        await self._broadcast_update(diagram_id, {
            "type": "living_refresh",
            "timestamp": datetime.now().isoformat()
        })


# Global canvas instance
_luuc_canvas = None


async def get_luuc_canvas() -> LUUCCanvas:
    """Get or create LUUC canvas singleton"""
    global _luuc_canvas

    if _luuc_canvas is None:
        media_store = MediaStore(data_dir="./data")
        _luuc_canvas = LUUCCanvas(media_store)

    return _luuc_canvas