import asyncio
import html
import shutil
from pathlib import Path
from datetime import datetime

from telethon import TelegramClient, events
from telethon.tl.types import User

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    TARGET_USER_ID,
    MAX_MEDIA_SIZE,
)

from database import (
    init_db,
    save_message,
    get_message,
    get_messages_by_message_id,
    update_message_text,
    save_edit,
    mark_deleted,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

TEMP_DIR = Path("data/temp")

TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# TELEGRAM CLIENTS
# ============================================================

user_client = TelegramClient(
    "user_session",
    API_ID,
    API_HASH
)

bot_client = TelegramClient(
    "bot_session",
    API_ID,
    API_HASH
)


# ID приватных диалогов
private_chat_ids = set()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def escape_text(text):
    if not text:
        return ""

    return html.escape(str(text))


def get_message_text(message):
    text = message.message

    if text:
        return text

    return ""


def is_bot_user(sender):
    """
    Проверяем, является ли отправитель ботом.

    Это предотвращает бесконечный цикл:
    пользователь -> наш аккаунт -> бот -> снова наш аккаунт -> ...
    """

    if isinstance(sender, User):
        return bool(sender.bot)

    return False


def profile_link(sender):
    """
    Создаёт кликабельную ссылку на профиль Telegram.

    Если есть username:
        https://t.me/username

    Если username нет:
        tg://user?id=USER_ID
    """

    if not sender:
        return None

    user_id = getattr(sender, "id", None)

    if not user_id:
        return None

    username = getattr(sender, "username", None)

    if username:
        url = f"https://t.me/{username}"
    else:
        url = f"tg://user?id={user_id}"

    return url


def get_sender_name(sender):
    """
    Получаем нормальное отображаемое имя.
    """

    if not sender:
        return "Неизвестный пользователь"

    first_name = getattr(sender, "first_name", None) or ""
    last_name = getattr(sender, "last_name", None) or ""

    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    username = getattr(sender, "username", None)

    if username:
        return f"@{username}"

    user_id = getattr(sender, "id", None)

    if user_id:
        return f"Пользователь {user_id}"

    return "Неизвестный пользователь"


def make_sender_line(sender):
    """
    Создаёт строку:

    👤 <a href="...">Имя Фамилия</a>

    Имя становится кликабельным.
    """

    if not sender:
        return "👤 Неизвестный пользователь"

    name = get_sender_name(sender)
    safe_name = escape_text(name)

    url = profile_link(sender)

    if url:
        safe_url = html.escape(url, quote=True)

        return (
            f'👤 <a href="{safe_url}">'
            f'{safe_name}'
            f'</a>'
        )

    return f"👤 {safe_name}"


def get_media_info(message):
    """
    Определяем тип медиа.
    """

    if not message.media:
        return None, None

    if message.photo:
        return "photo", None

    if message.video:
        return "video", None

    if message.voice:
        return "voice", None

    if message.audio:
        return "audio", None

    if message.gif:
        return "gif", None

    if message.document:
        filename = None

        if message.file:
            filename = message.file.name

        return "document", filename

    return "media", None


async def get_sender_info(message):
    """
    Получаем отправителя сообщения.
    """

    try:
        sender = await message.get_sender()
    except Exception:
        sender = None

    if not sender:
        return None, None, None

    sender_id = getattr(sender, "id", None)
    sender_name = get_sender_name(sender)
    sender_username = getattr(sender, "username", None)

    return sender, sender_id, sender_name


# ============================================================
# ОТПРАВКА УВЕДОМЛЕНИЙ
# ============================================================

async def send_notification(text):
    """
    Отправляет сообщение через нашего бота.
    """

    try:
        await bot_client.send_message(
            TARGET_USER_ID,
            text,
            parse_mode="html",
            link_preview=False
        )

    except Exception as e:
        print(f"[BOT ERROR] {e}")


async def send_media(
    message,
    sender,
    caption=""
):
    """
    Скачивает медиа во временную папку
    и отправляет его через бота.

    После отправки временный файл удаляется.
    """

    file_path = None

    try:
        if not message.media:
            return

        # Проверяем размер
        if message.file and message.file.size:
            if message.file.size > MAX_MEDIA_SIZE:
                await send_notification(
                    f"{make_sender_line(sender)}\n\n"
                    f"⚠️ Медиа слишком большое для отправки.\n"
                    f"Размер: {message.file.size / 1024 / 1024:.1f} MB"
                )
                return

        file_path = await message.download_media(
            file=str(TEMP_DIR)
        )

        if not file_path:
            await send_notification(
                f"{make_sender_line(sender)}\n\n"
                f"⚠️ Не удалось скачать медиа."
            )
            return

        media_type, media_name = get_media_info(message)

        media_caption = make_sender_line(sender)

        if caption:
            media_caption += f"\n\n{escape_text(caption)}"

        if media_type:
            media_caption += f"\n\n📎 {escape_text(media_type)}"

        if media_name:
            media_caption += f"\n📄 {escape_text(media_name)}"

        await bot_client.send_file(
            TARGET_USER_ID,
            file_path,
            caption=media_caption,
            parse_mode="html"
        )

    except Exception as e:
        print(f"[MEDIA ERROR] {e}")

        await send_notification(
            f"{make_sender_line(sender)}\n\n"
            f"⚠️ Ошибка обработки медиа:\n"
            f"{escape_text(str(e))}"
        )

    finally:
        # Удаляем временный файл
        if file_path:
            try:
                path = Path(file_path)

                if path.exists():
                    path.unlink()

            except Exception:
                pass


# ============================================================
# НОВОЕ СООБЩЕНИЕ
# ============================================================

@user_client.on(events.NewMessage(incoming=True))
async def new_message_handler(event):

    try:
        # Нас интересуют только личные диалоги
        if not event.is_private:
            return

        message = event.message

        # Получаем отправителя
        sender = await message.get_sender()

        # Не обрабатываем сообщения от ботов
        if is_bot_user(sender):
            return

        chat_id = event.chat_id

        if not chat_id:
            return

        # Запоминаем приватный чат
        private_chat_ids.add(chat_id)

        sender_id = getattr(sender, "id", None)
        sender_name = get_sender_name(sender)
        sender_username = getattr(sender, "username", None)

        text = get_message_text(message)

        media_type, media_name = get_media_info(message)

        # Сохраняем сообщение в БД ДО отправки уведомления.
        # Это важно для восстановления удалённых сообщений.
        save_message(
            chat_id=chat_id,
            message_id=message.id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_username=sender_username,
            text=text,
            media_type=media_type,
            media_name=media_name,
            date=now_iso()
        )

        print(
            f"[NEW] "
            f"{sender_name} "
            f"(chat={chat_id}, message={message.id})"
        )

        # ----------------------------------------------------
        # Сообщение с медиа
        # ----------------------------------------------------

        if message.media:

            await send_media(
                message,
                sender,
                caption=text
            )

            return

        # ----------------------------------------------------
        # Обычный текст
        # ----------------------------------------------------

        if text:

            notification = (
                f"{make_sender_line(sender)}\n\n"
                f"{escape_text(text)}"
            )

            await send_notification(notification)

    except Exception as e:

        print(f"[NEW MESSAGE ERROR] {e}")


# ============================================================
# РЕДАКТИРОВАНИЕ СООБЩЕНИЯ
# ============================================================

@user_client.on(events.MessageEdited(incoming=True))
async def edited_message_handler(event):

    try:

        if not event.is_private:
            return

        message = event.message

        sender = await message.get_sender()

        # Не обрабатываем сообщения от ботов
        if is_bot_user(sender):
            return

        chat_id = event.chat_id

        if not chat_id:
            return

        private_chat_ids.add(chat_id)

        # Ищем оригинальное сообщение
        old_message = get_message(
            chat_id,
            message.id
        )

        if not old_message:
            return

        old_text = old_message["text"] or ""
        new_text = get_message_text(message)

        # Если текст реально не изменился,
        # ничего не отправляем
        if old_text == new_text:
            return

        # Сохраняем историю изменения
        save_edit(
            chat_id=chat_id,
            message_id=message.id,
            old_text=old_text,
            new_text=new_text,
            edited_at=now_iso()
        )

        # Обновляем основную запись
        update_message_text(
            chat_id,
            message.id,
            new_text
        )

        print(
            f"[EDIT] "
            f"{get_sender_name(sender)} "
            f"(chat={chat_id}, message={message.id})"
        )

        notification = (
            f"✏️ {make_sender_line(sender)}\n\n"
            f"<b>Было:</b>\n"
            f"{escape_text(old_text) or '—'}\n\n"
            f"<b>Стало:</b>\n"
            f"{escape_text(new_text) or '—'}"
        )

        await send_notification(notification)

    except Exception as e:

        print(f"[EDIT ERROR] {e}")


# ============================================================
# УДАЛЕНИЕ СООБЩЕНИЯ
# ============================================================

@user_client.on(events.MessageDeleted())
async def deleted_message_handler(event):

    try:

        deleted_ids = event.deleted_ids

        if not deleted_ids:
            return

        print(
            f"[DELETE EVENT] "
            f"ids={list(deleted_ids)} "
            f"chat_id={event.chat_id}"
        )

        for message_id in deleted_ids:

            # ------------------------------------------------
            # Если Telegram передал chat_id —
            # ищем конкретно в этом чате.
            # ------------------------------------------------

            if event.chat_id:

                row = get_message(
                    event.chat_id,
                    message_id
                )

                candidates = []

                if row:
                    candidates.append(row)

            # ------------------------------------------------
            # Если chat_id отсутствует —
            # ищем по message_id во всей БД.
            # ------------------------------------------------

            else:

                candidates = get_messages_by_message_id(
                    message_id
                )

            if not candidates:
                print(
                    f"[DELETE] "
                    f"message_id={message_id} "
                    f"не найдено в БД"
                )
                continue

            for row in candidates:

                chat_id = row["chat_id"]

                # Работаем только с личными чатами
                if chat_id not in private_chat_ids:
                    continue

                # Уже было обработано
                if row["is_deleted"]:
                    continue

                sender_name = (
                    row["sender_name"]
                    or "Неизвестный пользователь"
                )

                sender_username = row["sender_username"]
                sender_id = row["sender_id"]

                # ------------------------------------------------
                # Создаём ссылку на отправителя из данных БД.
                # ------------------------------------------------

                if sender_username:

                    profile_url = (
                        f"https://t.me/"
                        f"{sender_username}"
                    )

                elif sender_id:

                    profile_url = (
                        f"tg://user?id="
                        f"{sender_id}"
                    )

                else:

                    profile_url = None

                safe_name = escape_text(sender_name)

                if profile_url:

                    sender_line = (
                        f'👤 <a href="'
                        f'{html.escape(profile_url, quote=True)}'
                        f'">{safe_name}</a>'
                    )

                else:

                    sender_line = f"👤 {safe_name}"

                old_text = row["text"] or ""

                # ------------------------------------------------
                # Уведомление
                # ------------------------------------------------

                notification = (
                    f"🗑️ <b>Сообщение удалено</b>\n\n"
                    f"{sender_line}\n\n"
                )

                if old_text:

                    notification += (
                        f"<b>Текст:</b>\n"
                        f"{escape_text(old_text)}"
                    )

                else:

                    media_type = row["media_type"]

                    if media_type:

                        notification += (
                            f"📎 Было удалено медиа: "
                            f"{escape_text(media_type)}"
                        )

                        if row["media_name"]:

                            notification += (
                                f"\n📄 "
                                f"{escape_text(row['media_name'])}"
                            )

                    else:

                        notification += (
                            "Текст сообщения отсутствует."
                        )

                await send_notification(
                    notification
                )

                mark_deleted(
                    chat_id,
                    message_id
                )

                print(
                    f"[DELETED] "
                    f"chat={chat_id}, "
                    f"message={message_id}"
                )

    except Exception as e:

        print(f"[DELETE ERROR] {e}")


# ============================================================
# ЗАГРУЗКА ПРИВАТНЫХ ДИАЛОГОВ
# ============================================================

async def load_private_dialogs():

    print("[INFO] Загружаю личные диалоги...")

    count = 0

    async for dialog in user_client.iter_dialogs():

        if dialog.is_user:

            private_chat_ids.add(dialog.id)

            count += 1

    print(
        f"[INFO] Личных диалогов загружено: {count}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    init_db()

    print("[INFO] Запуск Telegram user client...")

    await user_client.start()

    print("[INFO] User client запущен.")

    me = await user_client.get_me()

    print(
        f"[INFO] Авторизован как: "
        f"{get_sender_name(me)} "
        f"(ID: {me.id})"
    )

    await load_private_dialogs()

    print("[INFO] Запуск bot client...")

    await bot_client.start(
        bot_token=BOT_TOKEN
    )

    print("[INFO] Bot client запущен.")

    print()
    print("=" * 50)
    print(" TELEGRAM MONITOR ЗАПУЩЕН ")
    print("=" * 50)
    print()
    print("Мониторятся только личные сообщения.")
    print("Группы и каналы игнорируются.")
    print("Удаление и редактирование отслеживаются.")
    print("Ссылки на отправителей включены.")
    print()
    print("Для остановки нажмите Ctrl+C")
    print()

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("[INFO] Монитор остановлен.")

    except Exception as e:

        print()
        print(f"[FATAL ERROR] {e}")
