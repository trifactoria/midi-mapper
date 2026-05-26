from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.ws import ws_mgr


router = APIRouter()


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws_mgr.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive; client can send "ping"
    except WebSocketDisconnect:
        ws_mgr.disconnect(ws)
    except Exception:
        ws_mgr.disconnect(ws)
