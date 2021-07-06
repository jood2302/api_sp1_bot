import logging
import os
import time
import sys

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

logger.debug("Бот стартует")

# есть ли осевые environments
# если чего-то нет - ошибку в лог и завершение работы
try:
    env_variables = os.environ    
except Exception as e:
    logger.error(f'{e}, Ошибка os.environ, бот завершает работу.')
    sys.exit(1)

try:
    PRAKTIKUM_TOKEN = env_variables['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = env_variables['TELEGRAM_TOKEN']
    CHAT_ID = env_variables['TELEGRAM_CHAT_ID']
except KeyError as e:
    logger.error(f'{e}, Не прочитаны секреты, бот завершает работу.')
    sys.exit(2)

if not all((PRAKTIKUM_TOKEN, TELEGRAM_TOKEN, CHAT_ID)):
    logger.error(
        'Find null secret(s)',
        'Есть пустой секрет, бот завершает работу.'
    )
    sys.exit(3)
    
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
    
    verdict = 'От АПИ домашки получен неизвестный статус.'
        
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def parse_current_state(hw_state):
    if not hw_state['homeworks']:
        return 'Не найдено статусов проверки работы'
    return parse_homework_status(hw_state['homeworks'][0])


def get_homeworks(current_timestamp):
    url = PRAKTIKUM_API_URL    
    payload = {'from_date': current_timestamp}
    homework_statuses = requests.get(url, headers=HEADERS, params=payload)
    return homework_statuses.json()


def send_message(message):
    return bot.send_message(CHAT_ID, message)

def log_send_err_message(exception, err_description):
    message = f'Бот упал с ошибкой: {exception} {err_description}'
    logger.error(message)
    logger.info('Бот отправляет в Телеграм сообщение '
                'об ошибке в своей работе')
    send_message(message)
    return

def main():

    last_status = ''
    current_state = ''
    current_timestamp = int(time.time())  # Начальное значение timestamp

    pause = 10
    while True:
        try:
            current_state = get_homeworks(last_timestamp)
            current_status = parse_current_state(current_state)
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
