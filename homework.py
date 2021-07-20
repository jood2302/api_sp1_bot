import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'telegram_bot.log')

logger = logging.getLogger(__name__)
_log_format = ('%(asctime)s - [%(levelname)s] - %(name)s - '
               '(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
logging.basicConfig(
    level=logging.INFO,
    format=_log_format
)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5000000, backupCount=5)
stream_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logger.debug('Бот стартует')

# есть ли осевые environments
# если чего-то нет - ошибку в лог и завершение работы
env_variables = os.environ
try:
    PRAKTIKUM_TOKEN = env_variables['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = env_variables['TELEGRAM_TOKEN']
    CHAT_ID = env_variables['TELEGRAM_CHAT_ID']
except KeyError as e:
    logger.error(f'{e}, Не прочитаны секреты, бот завершает работу.')
    sys.exit(1)

bot = telegram.Bot(token=TELEGRAM_TOKEN)

PRAKTIKUM_API_URL = ('https://praktikum.yandex.ru/'
                     'api/user_api/homework_statuses/')
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}

HW_STATUSES = {
    'rejected': 'К сожалению, в работе нашлись ошибки.',
    'approved': 'Ревьюеру всё понравилось, работа зачтена!',
    'reviewing': 'Работа отправилась на ревью.'
}


def parse_homework_status(last_hw):
    """Парсинг словаря от АПИ.

    На входе : непустой словарь
    (первый эл-т списка по ключу 'homeworks' из json от АПИ).
    Если были изменения статуса работы, должен содержать в том числе ключи:
    'homework_name'
    'status'
    """
    # Если имя работы не пришло, так её и обозвать.
    homework_name = last_hw.get('homework_name', 'Нет имени работы')
    try:
        received_status = last_hw['status']
        verdict = HW_STATUSES[received_status]
    except KeyError as e:
        message = ('Ошибка ключа или во входном last_hw'
                   'или в глобальном HW_STATUSES')
        log_send_err_message(e, message)
        return (f'На запрос статуса работы "{homework_name}" '
                'получен неизвестный статус.')
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def log_send_err_message(exception, err_description):
    """Отправка сообщения об ошибке в лог и в Телеграм.

    На входе имя ошибки и описание.
    """
    message = ('В работе бота произошла ошибка: '
               f'{exception} {err_description}')
    logger.error(message)
    logger.info('Бот отправляет в Телеграм сообщение '
                'об ошибке в своей работе.')
    send_message(message)


def get_homeworks(timestamp):
    """Запрос АПИ домашки.

    На входе - момент времени в Unix-time.
    На выходе - словарь с последней домашкой, если получен,
    или пустой словарь, если были ошибки в соединении или ответе.
    В ответе на запрос ожидается json со словарём, где есть
    ключи 'homeworks' и 'current_date'.
    """
    payload = {'from_date': timestamp}
    hw_valid_json = dict()
    try:
        response = requests.get(
            PRAKTIKUM_API_URL,
            headers=HEADERS,
            params=payload
        )
        if response.status_code != requests.codes.ok:
            message = 'Сервер домашки не вернул статус 200.'
            log_send_err_message('Not HTTPStatus.OK', message)
            return {}

        # json.JSONDecodeError ver. Python >= 3
        hw_valid_json = response.json()
    except requests.ConnectionError as e:
        message = 'Ошибка соединения.'
        log_send_err_message(e, message)
    except requests.Timeout as e:
        message = f'Ошибка Timeout-а. {e}'
        log_send_err_message(e, message)
    except requests.RequestException as e:
        message = f'Ошибка отправки запроса. {e}'
        log_send_err_message(e, message)
    except json.JSONDecodeError as e:
        message = 'Не удалось прочитать json-объект.'
        log_send_err_message(e, message)

    return hw_valid_json


def main():
    # Начальное значение timestamp - момент старта main()
    current_timestamp = int(time.time())

    while True:
        try:
            current_resp_get = get_homeworks(current_timestamp)
            # ожидается список по ключу 'homeworks'
            # если ключа нет - обработка KeyError в блоке except.
            last_homeworks = current_resp_get['homeworks']
            # если список и если не пуст - парсим статус
            if isinstance(last_homeworks, list) and last_homeworks:
                current_status = parse_homework_status(
                    last_homeworks[0]
                )
                logger.info('Бот отправляет в Телеграм сообщение '
                            'об обновлении статуса домашки.')
                send_message(current_status)

            time.sleep(5 * 60)  # Опрашивать раз в пять минут

            # По ключу 'current_date' ожидается Unix-time
            # отметка момента ответа АПИ.
            # Если пришло None, время запроса не обновлять.
            # Если ключа нет - обработка KeyError в блоке except.
            last_timestapm = current_resp_get['current_date']
            if last_timestapm:
                current_timestamp = last_timestapm

        except KeyError as e:
            message = ('В ответе АПИ не найден ключ'
                       '"homeworks" или "current_date".')
            log_send_err_message(e, message)
            time.sleep(5)
        except Exception as e:
            message = 'В работе бота произошла ошибка.'
            log_send_err_message(e, message)
            time.sleep(5)


if __name__ == '__main__':
    main()
