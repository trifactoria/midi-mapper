import json
from typing import Any, Dict, List

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        if not self.clients:
            return
        msg = json.dumps(payload)
        dead: List[WebSocket] = []
        for c in self.clients:
            try:
                await c.send_text(msg)
            except Exception:
                dead.append(c)
        for d in dead:
            self.disconnect(d)


ws_mgr = WSManager()
