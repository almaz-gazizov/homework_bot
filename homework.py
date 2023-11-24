import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

DATA_ERROR = 'Отсутствуют обязательные переменные окружения'
DICT_ERROR = 'Ответ API не преобразован в словарь. Тип ответа: {type}'
HOMEWORKS_ERROR = 'Нет домашних работ'
HTTP_ERROR = 'Не доступен эндпоинт: {error}'
KEY_ERROR = 'Ошибка ключа {key}'
LIST_ERROR = (
    'Ответ API не содержит список под ключом "homeworks". '
    'Тип ответа: {type}'
)
PROGRAMM_ERROR = 'Сбой в работе программы: {error}'
SENDING_MESSAGE_ERROR = 'Ошибка при отправке сообщения: {error}'
SERVER_ERROR = 'Возникла ошибка при запросе к API: {error}'
STATUS_ERROR = 'Неопознанный статус - {status}'


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'main.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='UTF-8'
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all(
        (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    )


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    logger.info(f'Отправляем сообщение: {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(SENDING_MESSAGE_ERROR.format(error=error))
    logger.debug(f'Сообщение отправлено успешно: {message}')


def get_api_answer(timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса."""
    logger.debug('Отправляем запрос')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        logger.error(SERVER_ERROR.format(error=error))
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError(
            HTTP_ERROR.format(error=response.status_code)
        )
    return response.json()


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    logger.debug('Получили ответ')
    logger.info('Проверяем ответ API')
    if not isinstance(response, dict):
        raise TypeError(
            DICT_ERROR.format(type=type(response))
        )
    if 'homeworks' not in response:
        raise KeyError(KEY_ERROR.format(key='homeworks'))
    homeworks = response['homeworks']
    if 'current_date' not in response:
        raise KeyError(KEY_ERROR.format(key='current_date'))
    if not isinstance(homeworks, list):
        raise TypeError(
            LIST_ERROR.format(type=type(homeworks))
        )
    return homeworks


def parse_status(homework):
    """Извлекаем из информации о домашней работе статус этой работы."""
    logger.debug('Извлекаем статус домашней работы')
    if 'homework_name' not in homework:
        raise KeyError(KEY_ERROR.format(key='homework_name'))
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError(KEY_ERROR.format(key='status'))
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(STATUS_ERROR.format(status=homework_status))
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(DATA_ERROR)
        sys.exit(1)
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    recent_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logger.error(HOMEWORKS_ERROR)
            if message != recent_message:
                send_message(bot, message)
                recent_message = message
        except Exception as error:
            logger.error(PROGRAMM_ERROR.format(error=error))
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
