"""
WebSocket connection manager.
"""
import json
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for Unity communication."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        json_str = json.dumps(message)
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(json_str)
            except Exception:
                self.active_connections.remove(connection)

    @property
    def has_connections(self) -> bool:
        """Check if there are active connections."""
        return len(self.active_connections) > 0


# Global manager instance
manager = ConnectionManager()
