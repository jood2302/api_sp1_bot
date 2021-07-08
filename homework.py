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

PRAKTIKUM_TOKEN = ''
TELEGRAM_TOKEN = ''
CHAT_ID = ''
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'telegram_bot.log')

logger = logging.getLogger(__name__)
_log_format = ('%(asctime)s - [%(levelname)s] - %(name)s - '
               '(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
logging.basicConfig(
    level=logging.INFO,
    format=_log_format
)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5000000, backupCount=5)
logger.addHandler(handler)

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
del env_variables


bot = telegram.Bot(token=TELEGRAM_TOKEN)

PRAKTIKUM_API_URL = ('https://praktikum.yandex.ru/'
                     'api/user_api/homework_statuses/')
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}

HW_STATUSES = {
    'rejected': 'К сожалению, в работе нашлись ошибки.',
    'approved': 'Ревьюеру всё понравилось, работа зачтена!',
    'reviewing': 'Работа отправилась на ревью.',
    'unknown': 'От АПИ домашки получен неизвестный статус.',
    'notretrieved': 'Информация об изменении статуса не получена.'
}


def parse_homework_status(last_hw):
    """Парсинг словаря от АПИ.

    На входе : словарь (value по ключу 'homeworks' из json от АПИ).
    Если были изменения статуса работы, содержит в том числе ключи:
    'homework_name'
    'status'
    Если изменений статуса работы не было - словарь пуст.
    """
    if not last_hw:  # словарь в ответе АПИ пуст, то есть изменений нет
        return HW_STATUSES['notretrieved']

    # Если имя работы не пришло, так её и обозвать.
    homework_name = last_hw.get('homework_name', 'Нет имени работы')

    # Если ключа 'status' нет, оповестить.
    if 'status' in last_hw:
        status = last_hw['status']
        if status in HW_STATUSES:
            verdict = HW_STATUSES[status]
            return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'
    return HW_STATUSES['unknown']


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
                'об ошибке в своей работе')
    send_message(message)
    return


def get_homeworks(current_timestamp):
    payload = {'from_date': current_timestamp}
    err_flag = None
    # обработать возможные ошибки ответа
    # status == 200
    # json ValueError ver. Python < 3
    # json.JSONDecodeError ver. Python >= 3
    try:
        response = requests.get(
            PRAKTIKUM_API_URL,
            headers=HEADERS,
            params=payload
        )
    except requests.ConnectionError as e:
        message = 'Ошибка соединения.'
        log_send_err_message(e, message)
        err_flag = 1
    except requests.Timeout as e:
        message = f'Ошибка Timeout-а. {e}'
        log_send_err_message(e, message)
        err_flag = 2
    except requests.RequestException as e:
        message = f'Ошибка отправки запроса. {e}'
        log_send_err_message(e, message)
        err_flag = 3

    if response.status_code != requests.codes.ok:
        message = 'Сервер домашки не вернул статус 200.'
        log_send_err_message('Not HTTPStatus.OK', message)
        err_flag = 4

    try:
        hw_valid_json = response.json()
    except json.JSONDecodeError as e:
        message = 'Не удалось прочитать json-объект.'
        log_send_err_message(e, message)
        err_flag = 5

    if err_flag:
        return {}
    return hw_valid_json


def main():
    # Начальное значение статуса
    last_status = HW_STATUSES['notretrieved']

    # Начальное значение timestamp
    current_timestamp = int(time.time())

    pause = 10
    while True:
        if pause >= 60 * 20:
            pause = 10
        try:
            current_resp_get = get_homeworks(current_timestamp)
            # в json ожидается 'homeworks'
            last_homeworks = current_resp_get['homeworks']
        except KeyError as e:
            message = 'В ответе АПИ не найден ключ "homeworks".'
            log_send_err_message(e, message)

            time.sleep(pause)
            pause += 5
            continue

        if type(last_homeworks) != list:
            time.sleep(pause)
            pause += 5
            continue

        # в json ожидается 'current_date'
        current_timestamp = current_resp_get.get(
            'current_date',
            int(time.time())
        )

        if last_homeworks:
            current_status = parse_homework_status(last_homeworks[0])
        else:
            current_status = HW_STATUSES['notretrieved']

        if last_status != current_status:
            logger.info('Бот отправляет сообщение '
                        'об изменении статуса ДЗ')
            send_message(last_status)
        last_status = current_status

        time.sleep(20 * 60)  # Опрашивать раз в двадцать минут


if __name__ == '__main__':
    main()
