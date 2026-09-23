import asyncio
from collections import defaultdict

from fastapi import WebSocket


class RoomRealtime:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, room_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[room_id].add(websocket)

    async def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(room_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(room_id, None)

    async def publish(self, room_id: int, event: dict[str, object]) -> None:
        async with self._lock:
            connections = tuple(self._connections.get(room_id, ()))

        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(event)
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(room_id, websocket)


realtime = RoomRealtime()
