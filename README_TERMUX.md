# Установка в Termux

1. Установи Termux из F-Droid/официального источника.
2. В Termux:
   pkg update && pkg upgrade
   pkg install python nano unzip tmux
3. Разреши доступ к памяти:
   termux-setup-storage
4. Перейди в Downloads и распакуй ZIP:
   cd ~/storage/downloads
   unzip telegram_monitor_termux.zip
   cd telegram_monitor_termux
5. Установи зависимости:
   pip install -r requirements.txt
6. Создай config.py:
   cp config.py.example config.py
   nano config.py
7. Заполни API_ID, API_HASH, BOT_TOKEN и TARGET_USER_ID.
8. Запусти:
   python main.py

При первом запуске Telethon запросит номер, код Telegram и при необходимости пароль 2FA.

Для работы в фоне:
   tmux new -s telegram-monitor
   python main.py
Отсоединиться: Ctrl+B, затем D
Вернуться: tmux attach -t telegram-monitor

Для долгой работы Android желательно отключить оптимизацию батареи для Termux.

В проекте мониторятся только личные чаты. Группы и каналы игнорируются.
Текст сообщений сохраняется в SQLite. История изменений сохраняется.
Медиа временно скачивается, отправляется боту и затем удаляется.
Удалённое медиа не хранится постоянно.
Файлы *.session содержат данные авторизации — никому их не передавай.
