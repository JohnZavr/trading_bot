# FastAPI WebSocket Connection Manager

from fastapi import WebSocket
from typing import List
from starlette.websockets import WebSocketState


class ConnectionManager:
	def __init__(self):
		self.active_connections: List[WebSocket] = [] # Список активных WebSocket-соединений

	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		self.active_connections.append(websocket)

	def disconnect(self, websocket: WebSocket):
		if websocket in self.active_connections:
			self.active_connections.remove(websocket)

	async def broadcast(self, message: str):
		for connection in self.active_connections:
			if connection.application_state == WebSocketState.CONNECTED:
				await connection.send_text(message)
