import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
PRAKTIKUM_API_URL = ('https://praktikum.yandex.ru/'
                     'api/user_api/homework_statuses/')
# секунд в месяце (30 * 24 * 60 * 60) ~ 2600000
SECONDS_PER_MONTH = 2600000
HW_REJECT_STATUS = 'rejected'
HW_APPROVED_STATUS = 'approved'

bot = telegram.Bot(token=TELEGRAM_TOKEN)

logger = logging.getLogger(__name__)
_log_format = ('%(asctime)s - [%(levelname)s] - %(name)s - '
               '(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
logging.basicConfig(
    level=logging.DEBUG
)


def get_file_handler():
    file_handler = logging.RotatingFileHandler(
        "telegram_bot.log", maxBytes=5000000, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_log_format))
    return file_handler


def get_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_stream_handler())
    return logger


def parse_homework_status(last_hw):
    homework_name = last_hw['homework_name']
    if last_hw['status'] == HW_REJECT_STATUS:
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def parse_current_state(hw_state):
    if len(hw_state['homeworks']) == 0:
        return 'Не найдено статусов проверки работы'
    return parse_homework_status(hw_state['homeworks'][0])


def get_homeworks(current_timestamp):
    url = PRAKTIKUM_API_URL
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    homework_statuses = requests.get(url, headers=headers, params=payload)
    return homework_statuses.json()


def send_message(message):
    return bot.send_message(CHAT_ID, message)


def main():
    logger.debug("Бот стартует")
    last_status = ''
    current_state = ''
    current_timestamp = int(time.time())  # Начальное значение timestamp

    # запрос статуса с payload == (current_timestamp - месяц)
    month_ago = (current_timestamp - SECONDS_PER_MONTH,)
    while True:
        try:
            current_state = get_homeworks(month_ago)
        
        except Exception as e:
            logger.error(f'Бот упал с ошибкой: {e}')
            logger.info('Бот отправляет сообщение '
                        'об ошибке в своей работе')
            send_message(f'Бот упал с ошибкой: {e}')

            last_status = parse_current_state(current_state)
            last_timestamp = current_state['current_date']

            logger.info('Бот отправляет сообщение')
            send_message(last_status)
            time.sleep(5)
        else:
            break

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

            time.sleep(5)


if __name__ == '__main__':
    main()
