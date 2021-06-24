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


def parse_homework_status(last_hw):
    homework_name = last_hw['homework_name']
    if last_hw['status'] == HW_REJECT_STATUS: # "status":"rejected" in .json()
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def parse_current_state(hw_state):
    if len(hw_state['homeworks'] == 0):
        return f'Не найдено статусов проверки работы'
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
    current_timestamp = int(time.time())  # Начальное значение timestamp

    while True:
        try:
            # запрос статуса с payload == (current_timestamp - месяц)
            month_ago = (current_timestamp - SECONDS_PER_MONTH,)
            current_state = get_homeworks(month_ago)
            parse_current_state(current_state)

            time.sleep(20 * 60)  # Опрашивать раз в двадцать минут

        except Exception as e:
            print(f'Бот упал с ошибкой: {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()


"""Вам предстоит написать Телеграм-бота, который будет:
обращаться к API сервиса Практикум.Домашка;
узнавать, взята ли ваша домашка в ревью, проверена ли она, провалена или принята;
отправлять результат в ваш Телеграм-чат.


Бот должен логировать момент своего запуска (уровень DEBUG)

и каждую отправку сообщения (уровень INFO).

Сообщения уровня ERROR бот должен логировать и,
дополнительно, отправлять вам в Телеграм."""