# Homework Bot
## Описание:

Telegram-бот для определения статуса принятия работы. При обновлении статуса анализирует ответ API сервиса и отправляет пользователю соответствующее уведомление.

## Стек используемых технологий:

Python, Telegram API.

## Структура кода:

* Функция `main()`: в ней описана основная логика работы программы. Все остальные функции запускаются из неё.
* Функция `check_tokens()` проверяет доступность переменных окружения, которые необходимы для работы программы.
* Функция `get_api_answer()` делает запрос к единственному эндпоинту API-сервиса.
* Функция `check_response()` проверяет ответ API на соответствие документации.
* Функция `parse_status()` извлекает из информации о конкретной домашней работе статус этой работы.
* Функция `send_message()` отправляет сообщение в Telegram чат, определяемый переменной окружения TELEGRAM_CHAT_ID.

## Автор:

[Алмаз Газизов](https://github.com/almaz-gazizov)
