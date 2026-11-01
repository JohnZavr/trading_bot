# Entry point

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from pybit.exceptions import InvalidRequestError, FailedRequestError
from strategy import Bot

from contextlib import asynccontextmanager
import asyncio
import uvicorn
import json

from ws_connector import ConnectionManager
from sse_connector import msg_queue
from chart_formatter import *

from logger import setLogger
from dotenv import load_dotenv

logger = setLogger()

load_dotenv(override=True) # Загрузка переменных окружения

manager = ConnectionManager()

bot = Bot()


@asynccontextmanager
async def lifespan(app: FastAPI):

	try:
		bot.init_public_websocket()

		bot.subscribe_to_kline()
		bot.subscribe_to_ticker()

	except InvalidRequestError as err:
		logger.debug(f"ByBit Request Error | {err.status_code} | {err.message}")
	except FailedRequestError as err:
		logger.debug(f"ByBit Request Failed | {err.status_code} | {err.message}")
	except Exception as err:
		logger.debug(str(err))

	yield

	logger.warning("Shutting down the server...")

	if bot.task and not bot.task.done():
		bot.task.cancel()
		await asyncio.gather(bot.task, return_exceptions=True)

	bot.close_ws_connection() # Закрытие WebSocket-соединения Bybit

	logger.info("❌ The server has shut down.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get(
	"/",
	response_class=HTMLResponse,
	tags=["Basic endpoints"],
	summary="Home page"
)
@app.get(
	"/dashboard",
	response_class=HTMLResponse,
	tags=["Basic endpoints"],
	summary="Home page"
)
async def index(request: Request):
	return templates.TemplateResponse(request, "index.html")


@app.get(
	"/history/{limit}",
	tags=["Candles"],
	summary="Get history of candles"
)
def get_history_klines(limit: int):
	try:
		klines = bot.preload_history_klines(limit)
		return format_klines_for_chart(klines)

	except Exception as err:
		logger.error(str(err))
		return {"success": False, "message": str(err)}


@app.get(
	"/indicators/sma_double",
	tags=["Indicators"],
	summary="Get SMA-double indicator"
)
def get_sma_double():

	if len(bot.timestamps) > 0:
		prices = bot.close_prices.copy()
		timestamps = bot.timestamps.copy()

		if (bot.current_price is not None) and (bot.current_timestamp is not None):
			prices.append(bot.current_price)
			timestamps.append(bot.current_timestamp)

		fast_ma, slow_ma = bot.calculate_ma(prices)

		logger.info(f"📌 {len(prices)} => {len(timestamps)} => {len(fast_ma)} => {len(slow_ma)}")

		if len(timestamps) == len(fast_ma) == len(slow_ma):
			sma_fast = format_sma_for_chart(fast_ma, timestamps)
			sma_slow = format_sma_for_chart(slow_ma, timestamps)
			return {'fast': sma_fast, 'slow': sma_slow}

	return None


@app.websocket("/ws")
async def ws_stream(websocket: WebSocket):
	await manager.connect(websocket)
	logger.info("🚀 [FastAPI] WebSocket connection successfully established.")

	try:
		while True:

			if bot.current_candle is not None:
				chart_data = format_kline_for_chart(bot.current_candle)
				await manager.broadcast(json.dumps({'topic': "kline", 'data': chart_data}))

			if bot.ticker_data is not None:
				await manager.broadcast(json.dumps({'topic': "tickers", 'data': bot.ticker_data}))

			if len(bot.timestamps) > 0:
				prices = bot.close_prices.copy()
				timestamp = bot.timestamps[-1]

				if (bot.current_price is not None) and (bot.current_timestamp is not None):
					prices.append(bot.current_price)
					timestamp = bot.current_timestamp

				fast_ma, slow_ma = bot.calculate_ma(prices)

				message = {
					'topic': "sma_double",
					'data': {
						'fast': format_sma_value(fast_ma[-1], timestamp, int(bot.timeframe)*60),
						'slow': format_sma_value(slow_ma[-1], timestamp, int(bot.timeframe)*60)
					}
				}
				await manager.broadcast(json.dumps(message))

			await asyncio.sleep(0.5)

	except WebSocketDisconnect:
		manager.disconnect(websocket)
		logger.info("❌ [FastAPI] WebSocket connection closed.")


async def event_generator():
	while True:
		message = await msg_queue.get()
		yield {'data': json.dumps(message)}
		msg_queue.task_done()


@app.get(
	"/logs",
	tags=["Terminal"],
	summary="Stream of messages from the server"
)
async def sse_stream():
	return EventSourceResponse(event_generator())


@app.post(
	"/bot/start",
	tags=["Control signals"],
	summary="Launching the trading bot"
)
async def start_bot():
	if bot.task and not bot.task.done():
		return {"success": False, "message": "The bot is already running."}

	bot.task = asyncio.create_task(bot.run()) # Запуск бота
	return {"success": True, "message": "Launch command sent."}


@app.post(
	"/bot/stop",
	tags=["Control signals"],
	summary="Stopping the trading bot"
)
async def stop_bot():
	if not bot.task or bot.task.done():
		return {"success": False, "message": "The bot is not running."}

	bot.task.cancel()
	return {"success": True, "message": "Stop command sent."}


@app.get(
	"/bot/status",
	tags=["Control signals"],
	summary="Get the bot's current status"
)
async def get_status():
	return {"is_running": True if bot.task and not bot.task.done() else False}



if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
