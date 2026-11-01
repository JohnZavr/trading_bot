# Logger

import logging

def setLogger():

	# Создание логгера
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)  # Установка уровня логирования

	# Создание обработчика с логированием в консоль
	cons_handler = logging.StreamHandler()
	cons_handler.setLevel(logging.DEBUG)  # Установка уровня логирования

	# Создание обработчика с логированием в файл "errors.log"
	file_handler = logging.FileHandler("errors.log", mode="a", encoding="utf-8")
	file_handler.setLevel(logging.WARNING)  # Установка уровня логирования

	# Создание шаблона форматирования
	formatter = logging.Formatter("[%(asctime)s] #%(levelname).8s | %(name)s | %(message)s")

	# Установка обработчикам шаблона форматирования
	cons_handler.setFormatter(formatter)
	file_handler.setFormatter(formatter)

	# Добавление к логгеру обработчиков
	logger.addHandler(cons_handler)
	logger.addHandler(file_handler)

	return logger
