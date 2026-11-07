# Server-Sent Events (SSE) Message Handler

from asyncio import Queue
from datetime import datetime

msg_queue: Queue = Queue()

async def send_to_terminal(message: str):

	local_time = datetime.now().strftime("%H:%M:%S") # Получение текущего времени в формате "ЧЧ:ММ:СС"
	await msg_queue.put({'time': local_time, 'text': message})
