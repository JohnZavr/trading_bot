# Trading bot

from pybit.exceptions import InvalidRequestError, FailedRequestError
from bybit import Bybit

import pandas as pd
import ta.trend
import logging
import asyncio

from sse_connector import send_to_terminal

from config import *

logger = logging.getLogger()


class Bot(Bybit): # Реализует логику торговли
	def __init__(self):
		super().__init__()

		self.timeout = int(TIMEOUT)
		self.sma_fast = int(FAST_PERIOD)
		self.sma_slow = int(SLOW_PERIOD)
		self.base_qty = float(BASE_QTY)
		self.quote_qty = float(QUOTE_QTY)

		self.fast_values = None
		self.slow_values = None

		self.task = None


	def calculate_ma(self, prices):

		price_series = pd.Series(list(prices)) # Серия Pandas с ценами свечей

		# Вычисление простых скользящих средних (SMA)
		fast_ma = ta.trend.sma_indicator(price_series, self.sma_fast).values
		slow_ma = ta.trend.sma_indicator(price_series, self.sma_slow).values

		return fast_ma, slow_ma


	def get_sma_signal(self): # Определение пересечения скользящих средних

		if len(self.history_candles) < self.sma_slow:
			logger.info(f"Accumulating data: {len(self.history_candles)}/{self.sma_slow} candles...")
			return 0

		fast_ma, slow_ma = self.calculate_ma(self.close_prices) # Расчёт скользящих средних по ценам закрытия

		self.fast_values = fast_ma
		self.slow_values = slow_ma

		if fast_ma[-1] > slow_ma[-1] and fast_ma[-2] < slow_ma[-2]: # Быстрая пересекает медленную снизу вверх (crossover)
			return 1  # Сигнал на покупку
		elif fast_ma[-1] < slow_ma[-1] and fast_ma[-2] > slow_ma[-2]: # Быстрая пересекает медленную сверху вниз (crossunder)
			return -1  # Сигнал на продажу
		else:
			return 0  # Пересечения не было


	async def check_signals(self): # Проверка сигналов и отправка ордеров

		try:
			cross = self.get_sma_signal()

			logger.info(f"🚀 {cross}")

			if cross > 0 and not self.is_position():
				await self.place_market_order("Buy", self.quote_qty)
				await send_to_terminal(f"[BUY] Order successfully sent. Transaction amount: ${self.quote_qty}.")

			elif cross < 0 and self.is_position():
				await self.place_market_order("Sell", self.base_qty)
				await send_to_terminal(f"[SELL] Order successfully sent. Transaction amount: {self.base_qty} BTC.")

		except Exception as err:
			logger.error(str(err))


	async def loop(self): # Цикл проверки

		logger.info("🚀 The bot has started.")
		await send_to_terminal("The bot has started.")

		try:
			while True:
				await send_to_terminal("Signal check...")
				await self.check_signals()

				await asyncio.sleep(self.timeout)

		except asyncio.CancelledError:
			logger.warning("Stopping the bot...")
			await send_to_terminal("Stopping the bot...")
			raise

		finally:
			self.task = None
			logger.info("❌ The bot was stopped.")
			await send_to_terminal("The bot was stopped.")


	async def run(self): # Инициализация бота

		logger.info("Starting the Trading Bot...")
		await send_to_terminal("Starting the Trading Bot...")

		try:
			self.check_permissions()
			await send_to_terminal("Access rights verification was successful.")

			self.get_position_id()
			await send_to_terminal("Client Order ID of the last position received.")

			await self.loop()

		except InvalidRequestError as err:
			logger.debug(f"ByBit Request Error | {err.status_code} | {err.message}")
		except FailedRequestError as err:
			logger.debug(f"ByBit Request Failed | {err.status_code} | {err.message}")
		except Exception as err:
			logger.debug(str(err))
