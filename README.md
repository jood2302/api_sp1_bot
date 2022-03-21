# Яндекс.Практикум

# курс Python-разработчик

## студент  Ковылин Василий

## Проект sprint_7.  Бот-ассистент.

***

* Бот должен:

  раз в 10 минут опрашивать API сервиса Практикум.Домашка и проверять статус отправленной на ревью домашней работы;
  
  при обновлении статуса анализировать ответ API и отправлять соответствующее уведомление в Telegram;
  
  логировать свою работу и сообщать о важных проблемах сообщением в Telegram.

* Алгоритм работы бота:

  Бот-ассистент должен в бесконечном цикле выполнять такую последовательность операций:
  
    Отправлять запрос к API домашки на эндпоинт ENDPOINT (функция get_api_answer())
    
    Проверять полученный ответ на корректность; проверять, не изменился ли статус (функция check_response())
    
    Если статус изменился — анализировать его (функция parse_status()) и отправлять в Telegram сообщение, выбрав нужный вердикт (verdict) из вариантов в словаре HOMEWORK_STATUSES (функция send_message())
    
    Обновлять временную метку (current_timestamp) и ждать установленное время до следующей попытки (RETRY_TIME)
    
* Логирование

  Каждое сообщение в журнале должно состоять как минимум из даты и времени события, уровня важности события, описания события.
  
  Обязательно должны логироваться такие события:
  
  отсутствие обязательных переменных окружения во время запуска бота (уровень CRITICAL).
  
  удачная отправка любого сообщения в Telegram (уровень INFO);
  
  сбой при отправке сообщения в Telegram (уровень ERROR);
  
  недоступность эндпоинта https://practicum.yandex.ru/api/user_api/homework_statuses/ (уровень ERROR);
  
  любые другие сбои при запросе к эндпоинту (уровень ERROR);
  
  отсутствие ожидаемых ключей в ответе API (уровень ERROR);
  
  недокументированный статус домашней работы, обнаруженный в ответе API (уровень ERROR).
  
  События уровня ERROR нужно не только логировать, но и пересылать информацию о них в Telegram в тех случаях, когда это технически возможно (если API Telegram перестанет отвечать или при старте программы не окажется нужной переменной окружения — ничего отправить не получится).

***

Работа с проектом:

Клонировать репозиторий и перейти в его папку в командной строке:

```
git clone https://github.com/coherentus/api_sp1_bot
cd api_sp1_bot
```

Cоздать и активировать виртуальное окружение:

```
python -m venv venv
```

Для *nix-систем и MacOS:

```
source venv/bin/activate
```

Для windows-систем:

```
source venv/Scripts/activate
```

Установить зависимости из файла requirements.txt:

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Для круглосуточной работы проект можно задеплоить на какой-либо сервис.

В данном случае был использован https://www.heroku.com/

На HEROKU есть возможность связать своё приложение с репозиторием Github и управлять деплоем кода из панели управления HEROKU.

https://github.com/heroku/python-sample - пример репозитория, адаптированного для размещения на HEROKU.

Подробные инструкции есть в документации - https://devcenter.heroku.com/categories/deployment

Чтобы всё запустилось, в репозиторий нужно поместить два служебных файла:

* requirements.txt со списком зависимостей, чтобы Heroku знал, какие пакеты ему нужно установить;
* файл Procfile, в котором должна быть указана «точка входа» — файл, который должен быть выполнен для запуска проекта.

Секркты PRAKTIKUM_TOKEN, TELEGRAM_TOKEN и CHAT_ID, нужные для доступа к API Я.Домашки и Телеграма, на сервере HEROKU переданы через переменные окружения.
***
Принцип работы API Яндекс.Домашка

Для успешного запроса нужно:
* в заголовке запроса передать токен авторизации Authorization: OAuth <token> ;
* в GET-параметре from_date передать метку времени в формате Unix time.

  Пример запроса
```
import requests

url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
headers = {'Authorization': f'OAuth {<ваш токен>}'}
payload = {'from_date': <временная метка в формате Unix time>}.

# Делаем GET-запрос к эндпоинту url с заголовком headers и параметрами params
homework_statuses = requests.get(url, headers=headers, params=payload)

# Печатаем ответ API в формате JSON
print(homework_statuses.text)

# А можно ответ в формате JSON привести к типам данных Python и напечатать и его
# print(homework_statuses.json())
```
  
Если в запросе переданы валидный токен и временная метка, то после выполнения программы в терминале будет напечатан ответ API.
  
Примеры ответов API
  
API Практикум.Домашка возвращает ответы в формате JSON. В ответе содержатся два ключа:
  
* homeworks : значение этого ключа — список домашних работ;
* current_date : значение этого ключа — время отправки ответа.
  
При запросе с параметром from_date = 0 API вернёт список домашек за всё время:

```
{
  "homeworks":[
    {
      "id":124,
      "status":"rejected",
      "homework_name":"username__hw_python_oop.zip",
      "reviewer_comment":"Код не по PEP8, нужно исправить",
      "date_updated":"2020-02-13T16:42:47Z",
      "lesson_name":"Итоговый проект"
    },
    {
      "id":123,
      "status":"approved",
      "homework_name":"username__hw_test.zip",
      "reviewer_comment":"Всё нравится",
      "date_updated":"2020-02-11T14:40:57Z",
      "lesson_name":"Тестовый проект"
    },

    ...
  ],
  "current_date":1581604970
}
```
  
Если за выбранный интервал времени ни у одной из домашних работ не появился новый статус — список работ будет пуст:
```
{"homeworks":[],"current_date":1634074965}
```

Статус домашки (значение по ключу status ) может быть трёх типов:
* reviewing: работа взята в ревью;
* approved: ревью успешно пройдено;
* rejected: в работе есть ошибки, нужно поправить.
Если домашку ещё не взяли в работу — её не будет в выдаче.
