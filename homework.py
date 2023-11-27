import logging
import os
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

TOKENS = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

DATA_ERROR = 'Отсутствуют обязательные переменные окружения'
DICT_ERROR = 'Ответ API не преобразован в словарь. Тип ответа: {type}'
HOMEWORKS_ERROR = 'Нет домашних работ'
HTTP_ERROR = (
    'Не доступен эндпоинт: {status_code}. '
    'URL - {url}, заголовки - {headers}, время - {params}.'
)
KEY_ERROR = 'Ошибка ключа {key}'
LIST_ERROR = (
    'Ответ API не содержит список под ключом "homeworks". '
    'Тип ответа: {type}'
)
PROGRAMM_ERROR = 'Сбой в работе программы: {error}'
SENDING_MESSAGE_ERROR = 'Ошибка при отправке сообщения "{message}": {error}'
SERVER_ERROR = (
    'Возникла ошибка при запросе к API: '
    'URL - {url}, заголовки - {headers}, время - {params}.'
)
SERVICE_ERROR = (
    'Сбой сервера: {code} - {error}. '
    'URL - {url}, заголовки - {headers}, время - {params}.'
)
STATUS_ERROR = 'Неопознанный статус - {status}'

SUCCESS_SENDING_MESSAGE = 'Сообщение отправлено успешно: {message}'
STATUS_UPDATED = 'Изменился статус проверки работы "{name}". {verdict}'


class ServerError(Exception):
    """Ошибка сервера Яндекс.Практикум."""

    pass


logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    for key in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if key is None:
            return False
        if not key:
            return False
    return True


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    logger.info(f'Отправляем сообщение: {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.exception(
            SENDING_MESSAGE_ERROR.format(error=error, message=message)
        )
    logger.debug(SUCCESS_SENDING_MESSAGE.format(message=message))


def get_api_answer(timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса."""
    logger.debug('Отправляем запрос')
    params = {'from_date': timestamp}
    request_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**request_params)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(
            SERVER_ERROR.format(**request_params)
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise ServerError(
            HTTP_ERROR.format(
                status_code=response.status_code,
                **request_params
            )
        )
    for item in ('code', 'error'):
        if item in response.json():
            raise ServerError(SERVICE_ERROR.format(
                    code=response.json['code'],
                    error=response.json['error'],
                    **request_params
                )
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
    name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError(KEY_ERROR.format(key='status'))
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(STATUS_ERROR.format(status=status))
    verdict = HOMEWORK_VERDICTS[status]
    return STATUS_UPDATED.format(name=name, verdict=verdict)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(DATA_ERROR)
        return
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    recent_message = ''
    prev_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logger.error(HOMEWORKS_ERROR)
            if message != recent_message and send_message(bot, message):
                recent_message = message
                timestamp = response.get('current_date')
        except Exception as new_error:
            error = PROGRAMM_ERROR.format(error=new_error)
            logger.exception(error)
            if prev_error != error and send_message(bot, error):
                prev_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s - %(levelname)s - %(name)s - '
            '%(funcName)s - %(lineno)s - %(message)s'
        )
    )
    handler = RotatingFileHandler(
        f'{__file__}.log',
        maxBytes=50000000,
        backupCount=5,
        encoding='UTF-8'
    )
    logger.addHandler(handler)
    main()
