# Telegram Private Monitor

Telegram-монитор для отслеживания личных сообщений Telegram-аккаунта.

Программа работает через [Telethon](https://github.com/LonamiWebs/Telethon) и отдельного Telegram-бота для отправки уведомлений.

## Возможности

- 📩 Отслеживание новых сообщений в личных чатах
- ✏️ Отслеживание редактирования сообщений
- 🗑️ Уведомления об удалении сообщений
- 👤 Кликабельная ссылка на профиль отправителя
- 📎 Передача фотографий, видео, документов, голосовых сообщений и другого медиа
- 💾 Сохранение сообщений и истории изменений в SQLite
- 🚫 Группы и каналы не отслеживаются
- 🤖 Защита от зацикливания сообщений от самого бота
- 🧹 Автоматическое удаление временных файлов
- 📱 Работает на Android через Termux

## Как это работает

Программа использует два Telegram-клиента:

1. Telethon авторизуется как обычный пользовательский аккаунт.
2. Пользовательский клиент получает сообщения из личных чатов.
3. Сообщения сохраняются в SQLite.
4. Медиа временно скачивается.
5. Telegram-бот отправляет уведомление на указанный аккаунт.
6. Временные файлы удаляются.

## Требования

- Python 3
- Telegram API ID
- Telegram API Hash
- Telegram Bot Token
- Android + Termux или обычный Linux

## Установка

Клонируйте репозиторий:

```bash
git clone https://github.com/Mereoreon/telegram-private-monitor.git
cd telegram-private-monitor
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Создайте `config.py` на основе `config.py.example` и укажите свои данные Telegram API и Bot Token.

Запустите программу:

```bash
python main.py
```

При первом запуске Telethon попросит авторизовать Telegram-аккаунт.

## Запуск в Termux

Для работы в фоне можно использовать `tmux`:

```bash
pkg install tmux
tmux new -s telegram-monitor
python main.py
```

Чтобы оставить программу работать в фоне:

```text
Ctrl+B
D
```

Вернуться к запущенной программе:

```bash
tmux attach -t telegram-monitor
```

При необходимости можно использовать:

```bash
termux-wake-lock
```

## Структура проекта

```text
telegram-private-monitor/
├── main.py
├── database.py
├── config.py.example
├── requirements.txt
├── README.md
├── README_TERMUX.md
├── .gitignore
└── LICENSE
```

## Безопасность

Никогда не публикуйте в GitHub:

- `config.py`
- Telegram Bot Token
- API Hash
- файлы `.session`
- базу данных `messages.db`
- папку `data/`

Секретные файлы добавлены в `.gitignore`.

## Лицензия

Проект распространяется под лицензией MIT.

## Репозиторий

GitHub:

https://github.com/Mereoreon/telegram-private-monitor
