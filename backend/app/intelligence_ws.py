from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class IntelligenceConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected: list[WebSocket] = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


intelligence_manager = IntelligenceConnectionManager()


async def intelligence_websocket_endpoint(websocket: WebSocket) -> None:
    await intelligence_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        intelligence_manager.disconnect(websocket)
