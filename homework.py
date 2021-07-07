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

logger.debug("Бот стартует")

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
    'reviewing': 'Работа отправилась на ревью.'
}


def parse_homework_status(last_hw):
    homework_name = last_hw['homework_name']
    status = last_hw['status']
    if status in HW_STATUSES:
        verdict = HW_STATUSES[status]
        return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'
    return 'От АПИ домашки получен неизвестный статус.'


def parse_current_state(hw_state):
    if not hw_state['homeworks']:
        return 'Не найдено статусов проверки работы'
    return parse_homework_status(hw_state['homeworks'][0])


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
    # обработать возможные ошибки ответа
    # status == 200
    # json ValueError ver. Python < 3
    # успех вызова r.json() не указывает на успех ответа. 
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
    except requests.Timeout as e:
        message = f'Ошибка Timeout-а. {e}'
        log_send_err_message(e, message)
    except requests.RequestException as e:
        message = f'Ошибка отправки запроса. {e}'
        log_send_err_message(e, message)

    try:
        response.raise_for_status()    
    except requests.exceptions.HTTPError as e:
        message = 'Сервер домашки не вернул статус 200.'
        log_send_err_message(e, message)
    
    try:
        hw_valid_json = response.json()
    except json.JSONDecodeError as e:
        message = 'Не удалось прочитать json-объект.'
        log_send_err_message(e, message)

    return hw_valid_json




def main():

    last_status = ''
    current_state = ''
    current_timestamp = int(time.time())  # Начальное значение timestamp

    pause = 10
    while True:
        try:
            current_state = get_homeworks(current_timestamp)
            current_status = parse_current_state(current_state)
            last_status = current_status
            if last_status != current_status:
                logger.info('Бот отправляет сообщение '
                            'об изменении статуса ДЗ')
                send_message(last_status)
            last_status = current_status

            time.sleep(20 * 60)  # Опрашивать раз в двадцать минут

        except Exception as e:
            logger.error(f'Бот упал с ошибкой: {e}')
            logger.info('Бот отправляет сообщение '
                        'об ошибке в своей работе')
            send_message(f'Бот упал с ошибкой: {e}')

            time.sleep(pause)
            pause += 5


if __name__ == '__main__':
    main()
