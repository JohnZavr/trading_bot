# Formatting data for Lightweight Charts

import pandas as pd

def format_klines_for_chart(klines):

	chart_series = []

	for kline in klines:
		chart_series.append({
			"time": int(kline[0]) // 1000,
			"open": float(kline[1]),
			"high": float(kline[2]),
			"low": float(kline[3]),
			"close": float(kline[4])
		})

	return chart_series


def format_kline_for_chart(kline):

	chart_candle = {
		"time": kline.get('start') // 1000,
		"open": float(kline.get('open')),
		"high": float(kline.get('high')),
		"low": float(kline.get('low')),
		"close": float(kline.get('close'))
	}

	return chart_candle


def format_sma_for_chart(values, timestamps):

	sma_series = []

	for idx in range(len(values)):
		if pd.isna(values[idx]):
			continue

		sma_series.append({
			"time": int(timestamps[idx]) // 1000,
			"value": float(values[idx])
		})

	return sma_series


def format_sma_value(value, timestamp, timeframe):

	total = int(timestamp) // 1000
	start_time = (total // timeframe) * timeframe

	sma_dot = {
		"time": start_time,
		"value": float(value)
	}

	return sma_dot
