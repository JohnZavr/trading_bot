
const terminal = document.getElementById('terminal');
const statusLine = document.getElementById('status-line');

function connectEventStream() {
	const eventSource = new EventSource("/logs"); // Подключение к стриму с помощью EventSource

	eventSource.onmessage = (event) => {
		const message = JSON.parse(event.data);

		const logLine = document.createElement('div'); // Создание контейнера для новой строки
		logLine.className = "log-line";

		const timestamp = document.createElement('span'); // Добавление временной метки
		timestamp.className = "log-timestamp";
		timestamp.innerText = `[${message.time}]`;

		const logText = document.createElement('span'); // Добавление текста сообщения
		logText.className = "log-text";
		logText.innerText = message.text;

		logLine.appendChild(timestamp);
		logLine.appendChild(logText);

		// Расстояние, на которое прокручен терминал от нижнего края (в пикселях)
		const scrollBottom = terminal.scrollHeight - terminal.clientHeight - terminal.scrollTop;

		terminal.insertBefore(logLine, statusLine); // Вставка лога перед строкой с курсором

		if (scrollBottom <= 5) { // Погрешность в 5px нужна для надежности при масштабировании
			terminal.scrollTop = terminal.scrollHeight;
		}
	};

	eventSource.onerror = () => {
		console.log("SSE connection lost or complete.");
		eventSource.close(); // Закрытие соединения
		statusLine.remove(); // Убираем курсор
	};
}

connectEventStream();
