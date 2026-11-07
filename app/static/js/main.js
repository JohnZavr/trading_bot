
const chartContainer = document.getElementById('chart-container');
const currentPrice = document.getElementById('current-price');
const startButton = document.getElementById('start-btn');
const stopButton = document.getElementById('stop-btn');
const statusLight = document.getElementById('status-light');
const statusText = document.getElementById('status-txt');

const chart = LightweightCharts.createChart(chartContainer, {
	width: chartContainer.clientWidth,
	height: 700,
	layout: {
		backgroundColor: '#f2f5f9',
		textColor: '#000'
	},
	grid: {
		vertLines: { color: '#dcdcdc' },
		horzLines: { color: '#dcdcdc' }
	},
	timeScale: {
		timeVisible: true,
		secondsVisible: false
	}
});

const candlestickSeries = chart.addCandlestickSeries({
	upColor: '#10b981',
	downColor: '#ef4444',
	borderVisible: false,
	wickUpColor: '#10b981',
	wickDownColor: '#ef4444'
});

const smaFastSeries = chart.addLineSeries({
	color: '#ff6d00',
	lineWidth: 2
});

const smaSlowSeries = chart.addLineSeries({
	color: '#2962ff',
	lineWidth: 2
});

window.addEventListener('resize', () => {
	chart.resize(chartContainer.clientWidth, 700);
});

function connectWebsocket() {
	console.log("WebSocket connection...");
	const websocket = new WebSocket("/ws");

	websocket.onopen = () => {
		console.log("WebSocket connection established.");
	};

	websocket.onmessage = (event) => {
		const message = JSON.parse(event.data);

		if (message.topic == "kline") {
			const candle = message.data;
			candlestickSeries.update(candle);
		}
		else if (message.topic == "tickers") {
			const ticker = message.data;
			currentPrice.innerText = ticker.lastPrice;
		}
		else if (message.topic == "sma_double") {
			const smaDots = message.data;

			if (smaDots.fast) {
				smaFastSeries.update(smaDots.fast);
			}
			if (smaDots.slow) {
				smaSlowSeries.update(smaDots.slow);
			}
		}
	};

	websocket.onerror = (err) => {
		console.error("WebSocket error:", err);
	};

	websocket.onclose = () => {
		console.log("WebSocket connection closed.");
		setTimeout(loadChartData, 5000); // Автоматическое переподключение при обрыве соединения
		setTimeout(() => {
			loadIndicator('/indicators/sma_double');
		}, 5500);
	};
}

async function loadChartData() {
	console.log("Request for historical data...");
	try {
		const response = await fetch("/history/250");
		const historyData = await response.json();

		if (historyData.error) {
			console.error(historyData.error);
		}
		else if (historyData.length > 0) {
			candlestickSeries.setData(historyData);
			console.log(`Successfully rendered ${historyData.length} candles.`);
		}
		else {
			console.warn("An empty array of historical data was returned.");
		}

		connectWebsocket();

	} catch (err) {
		console.error("Error loading history:", err);
	}
}

loadChartData();

async function loadIndicator(url) {
	console.log("Request for SMA indicator data...");
	try {
		const response = await fetch(url);
		const smaData = await response.json();

		if (smaData.error) {
			console.error(smaData.error);
		}
		else if (smaData.fast.length > 0 && smaData.slow.length > 0) {
			smaFastSeries.setData(smaData.fast);
			smaSlowSeries.setData(smaData.slow);
			console.log(`[SMA FAST] Successfully rendered ${smaData.fast.length} points.`);
			console.log(`[SMA SLOW] Successfully rendered ${smaData.slow.length} points.`);
		}
		else {
			console.warn("An empty array of SMA indicator data was returned.");
		}

	} catch (err) {
		console.error("Error loading indicator:", err);
	}
}

setTimeout(() => {
	loadIndicator('/indicators/sma_double');
}, 1000);

async function sendSignal(url) {
	const response = await fetch(url, { method: 'POST' });
	const data = await response.json();
	console.log(data.message);
	checkStatus();
}

async function checkStatus() {
	const response = await fetch("/bot/status");
	const data = await response.json();

	if (data.is_running) {
		statusText.innerText = "RUNNING";
		statusLight.className = "active";
	}
	else {
		statusText.innerText = "STOPPED";
		statusLight.className = "inactive";
	}
}

checkStatus();

startButton.addEventListener('click', () => {
	sendSignal('/bot/start');
	loadIndicator('/indicators/sma_double');
});

stopButton.addEventListener('click', () => {
	sendSignal('/bot/stop');
});
