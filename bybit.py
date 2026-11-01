# Bybit exchange

from pybit.unified_trading import HTTP, WebSocket
from collections import deque

import logging
import random
import string
import math
import os

from config import *

logger = logging.getLogger()


class Bybit: # Реализует логику взаимодействия с биржей Bybit
	def __init__(self):
		self.session = HTTP(
			testnet=False,
			demo=IS_DEMO,
			api_key=os.getenv('BYBIT_DEMO_API_KEY'),
			api_secret=os.getenv('BYBIT_DEMO_SECRET_KEY'),
			max_retries=10,
			retry_delay=5,  # в секундах
			recv_window=60000,
			return_response_headers=False
		)
		self.symbol = SYMBOL
		self.category = CATEGORY
		self.timeframe = TIMEFRAME
		self.position_id = None

		self.ws_public = None
		self.ws_private = None

		self.history_candles = deque(maxlen=BUFFER_SIZE) # Двусторонняя очередь (Буфер)
		self.current_candle = None

		self.close_prices = deque(maxlen=BUFFER_SIZE) # Очередь цен закрытия
		self.current_price = None

		self.timestamps = deque(maxlen=BUFFER_SIZE) # Начальные временные метки свечей (в миллисекундах)
		self.current_timestamp = None

		self.ticker_data = None


	def check_permissions(self): # Проверка прав доступа, используя предоставленные ключи
		response = self.session.get_wallet_balance(accountType="UNIFIED") # Запрос на получение баланса кошелька


	def handle_message(self, message):
		print(f"📌{message}")


	def handle_kline_message(self, message):

		if "kline" not in message.get('topic', ""):
			return

		candle_data = message.get('data', [])[0]
		close_price = float(candle_data.get('close'))
		timestamp = candle_data.get('start')
		is_confirmed = candle_data.get('confirm')  # True - свеча закрылась, False - формируется

		if is_confirmed:
			self.history_candles.append(candle_data)
			self.close_prices.append(close_price)
			self.timestamps.append(timestamp)
			self.current_candle = None  # Сброс временной свечи
			self.current_price = None
			self.current_timestamp = None
			logger.info("✅ [CLOSED] The candle has been added to history.")
		else:
			self.current_candle = candle_data
			self.current_price = close_price
			self.current_timestamp = timestamp


	def handle_ticker_message(self, message):

		if "tickers" not in message.get('topic', ""):
			return

		self.ticker_data = message.get('data', {})


	def init_public_websocket(self):

		self.ws_public = WebSocket(
			testnet=False,
			channel_type=self.category
		)
		logger.info("🚀 [Bybit] WebSocket connection successfully established.")


	def subscribe_to_kline(self): # Подписка на получение свечей в реальном времени

		self.ws_public.kline_stream(
			interval=int(self.timeframe),
			symbol=self.symbol,
			callback=self.handle_kline_message
		)


	def subscribe_to_ticker(self): # Подписка на получение тикеров в реальном времени

		self.ws_public.ticker_stream(
			symbol=self.symbol,
			callback=self.handle_ticker_message
		)


	def init_private_websocket(self):

		self.ws_private = WebSocket(
			testnet=False,
			channel_type="private",
			api_key=os.getenv('BYBIT_DEMO_API_KEY'),
			api_secret=os.getenv('BYBIT_DEMO_SECRET_KEY')
		)

		self.ws_private.wallet_stream(callback=self.handle_message)


	def close_ws_connection(self):

		self.ws_public.exit() # для sdk pybit
		logger.info("❌ [Bybit] WebSocket connection closed.")


	def preload_history_klines(self, limit=int(HISTORY_LIMIT)): # Предзагрузка истории свечей

		response = self.session.get_kline(
			category=self.category,
			symbol=self.symbol,
			interval=self.timeframe,
			limit=limit
		)

		klines = response.get('result', {}).get('list', [])
		klines.reverse()

		self.history_candles.extend(klines)									# Исторические данные свечей
		self.close_prices.extend([float(candle[4]) for candle in klines])	# Цены закрытия
		self.timestamps.extend([int(candle[0]) for candle in klines])		# Начальные временные метки

		logger.info(f"✅ Candle history loaded. Successfully received {len(klines)} candles.")
		return klines


	async def place_market_order(self, side, qty): # Отправка рыночного ордера

		link_id = self.generate_id(length=ID_LENGTH, prefix=ID_PREFIX)

		response = self.session.place_order(
			category=self.category,
			symbol=self.symbol,
			side=side.capitalize(),
			orderType="Market",
			qty=qty,
			orderLinkId=link_id
		)

		# side="Buy"  => qty=USDT, marketUnit="quoteCoin" (default)
		# side="Sell" => qty=BTC,  marketUnit="baseCoin"  (default)

		order_id = None
		if response.get('retCode') == 0:
			order_id = response.get('result', {}).get('orderId')
			self.position_id = link_id

			logger.info(f"✅ [{side.upper()}] Order has been placed successfully! Order ID: {order_id}, Link ID: {self.position_id}")
		else:
			logger.error(response)

		return order_id


	def is_position(self): # Поиск открытой позиции по orderLinkId

		order_list = self.session.get_order_history(
			category=self.category,
			symbol=self.symbol,
			orderStatus="Filled"
		).get('result', {}).get('list', [])

		for order in order_list:
			if order.get('orderLinkId') == self.position_id:
				logger.debug(f"⚠️ Order ID: {order.get('orderId')} [{order.get('side').upper()}]")

				return order.get('side').lower() == "buy"

		return False


	def get_position_id(self):

		order_list = self.session.get_order_history(
			category=self.category,
			symbol=self.symbol,
			orderStatus="Filled"
		).get('result', {}).get('list', [])

		for order in order_list:
			if order.get('orderLinkId').startswith(ID_PREFIX):
				self.position_id = order.get('orderLinkId')
				logger.debug(f"⚠️ Order ID: {order.get('orderId')} Link ID: {order.get('orderLinkId')} [{order.get('side').upper()}]")
				return


	def generate_id(self, length=10, prefix=""):

		return prefix + self.generate_random_string(length)


	def get_assets(self, coin):

		response = self.session.get_wallet_balance(accountType="UNIFIED")
		assets = {}

		for asset in response.get('result', {}).get('list', [])[0].get('coin', []):
			assets[asset.get('coin')] = float(asset.get('walletBalance', '0.0'))

		return assets.get(coin, 0.0)


	@staticmethod
	def round_floor(value, decimals):

		factor = 10 ** decimals
		return math.floor(value * factor) / factor


	@staticmethod
	def generate_random_string(length):

		characters = string.digits + string.ascii_letters

		random_string = "".join(random.choices(characters, k=length))
		return random_string
