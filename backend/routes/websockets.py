from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Dict, Set
import json
from datetime import datetime, timezone, timedelta

from backend.database import get_session
from backend.models import Chat, User
from backend.auth_utils import get_client_from_header

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)


def ist_now() -> datetime:
    """Get current IST datetime"""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)


def ist_now_iso() -> str:
    """Get current IST time as ISO string"""
    return ist_now().isoformat()


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    # Convert to IST
    ist = timezone(timedelta(hours=5, minutes=30))
    return utc_dt.astimezone(ist)


# Connection manager to track active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # Store connections by session_id
        # Format: {session_id: {client_id: websocket, "admin": websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, connection_type: str):
        """Connect a new WebSocket client"""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}

        self.active_connections[session_id][connection_type] = websocket
        print(f"✅ {connection_type} connected to session {session_id}")
        print(f"📊 Active connections: {len(self.active_connections)}")

    def disconnect(self, session_id: str, connection_type: str):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            if connection_type in self.active_connections[session_id]:
                del self.active_connections[session_id][connection_type]
                print(f"❌ {connection_type} disconnected from session {session_id}")

            # Clean up empty session
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_to_session(self, session_id: str, message: dict, exclude: str = None):
        """Send message to all connections in a session (except excluded one)"""
        if session_id not in self.active_connections:
            return

        for conn_type, websocket in self.active_connections[session_id].items():
            if conn_type != exclude:
                try:
                    await websocket.send_json(message)
                    print(f"📤 Sent message to {conn_type} in session {session_id}")
                except Exception as e:
                    print(f"❌ Failed to send to {conn_type}: {e}")

    async def send_to_admin(self, session_id: str, message: dict):
        """Send message specifically to admin"""
        if session_id in self.active_connections:
            admin_ws = self.active_connections[session_id].get("admin")
            if admin_ws:
                try:
                    await admin_ws.send_json(message)
                    print(f"📤 Sent message to admin in session {session_id}")
                except Exception as e:
                    print(f"❌ Failed to send to admin: {e}")

    async def send_to_client(self, session_id: str, message: dict):
        """Send message specifically to client"""
        if session_id in self.active_connections:
            client_ws = self.active_connections[session_id].get("client")
            if client_ws:
                try:
                    await client_ws.send_json(message)
                    print(f"📤 Sent message to client in session {session_id}")
                except Exception as e:
                    print(f"❌ Failed to send to client: {e}")


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/client/{session_id}")
async def websocket_client_endpoint(
    websocket: WebSocket,
    session_id: str,
    chatbot_key: str = None
):
    """WebSocket endpoint for chatbot clients"""
    await manager.connect(websocket, session_id, "client")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            print(f"📩 Received from client in session {session_id}: {data}")

            message_type = data.get("type")

            if message_type == "user_message":
                # User sent a message - broadcast to admin with IST timestamp
                await manager.send_to_admin(session_id, {
                    "type": "new_user_message",
                    "session_id": session_id,
                    "message": data.get("message"),
                    "timestamp": ist_now_iso()  # IST timestamp
                })

            elif message_type == "typing":
                # User is typing - notify admin
                await manager.send_to_admin(session_id, {
                    "type": "user_typing",
                    "session_id": session_id,
                    "is_typing": data.get("is_typing", False)
                })

            elif message_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "client")
        # Notify admin that client disconnected
        await manager.send_to_admin(session_id, {
            "type": "client_disconnected",
            "session_id": session_id
        })

    except Exception as e:
        print(f"❌ Client WebSocket error: {e}")
        manager.disconnect(session_id, "client")


@router.websocket("/admin/{session_id}")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = None
):
    """WebSocket endpoint for admin dashboard"""

    # TODO: Verify admin token here
    # For now, accepting connection

    await manager.connect(websocket, session_id, "admin")

    try:
        while True:
            # Receive message from admin
            data = await websocket.receive_json()

            print(f"📩 Received from admin in session {session_id}: {data}")

            message_type = data.get("type")

            if message_type == "admin_reply":
                # Admin sent a reply - broadcast to client with IST timestamp
                await manager.send_to_client(session_id, {
                    "type": "admin_message",
                    "message": data.get("message"),
                    "timestamp": ist_now_iso(),  # IST timestamp
                    "admin_override": True
                })

            elif message_type == "typing":
                # Admin is typing - notify client
                await manager.send_to_client(session_id, {
                    "type": "admin_typing",
                    "is_typing": data.get("is_typing", False)
                })

            elif message_type == "delete_message":
                # Admin deleted a message - notify client
                await manager.send_to_client(session_id, {
                    "type": "message_deleted",
                    "message_id": data.get("message_id")
                })

            elif message_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id, "admin")
        print(f"📴 Admin disconnected from session {session_id}")

    except Exception as e:
        print(f"❌ Admin WebSocket error: {e}")
        manager.disconnect(session_id, "admin")


@router.post("/broadcast/{session_id}")
async def broadcast_message(
    session_id: str,
    message: dict,
    session: AsyncSession = Depends(get_session)
):
    """
    HTTP endpoint to broadcast a message to a session
    Useful for triggering WebSocket messages from other parts of the app
    """
    await manager.send_to_session(session_id, message)
    return {"status": "broadcasted"}
