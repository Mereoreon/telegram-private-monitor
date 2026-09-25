import sqlite3
from pathlib import Path


# ============================================================
# НАСТРОЙКИ
# ============================================================

DB_PATH = Path("data/messages.db")


# ============================================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ
# ============================================================

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# СОЗДАНИЕ БАЗЫ
# ============================================================

def init_db():

    with get_connection() as conn:

        # ----------------------------------------------------
        # Сообщения
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                sender_id INTEGER,
                sender_name TEXT,
                sender_username TEXT,

                text TEXT,

                media_type TEXT,
                media_name TEXT,

                date TEXT,

                is_deleted INTEGER DEFAULT 0,

                PRIMARY KEY (chat_id, message_id)
            )
        """)

        # ----------------------------------------------------
        # История редактирования
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                old_text TEXT,
                new_text TEXT,

                edited_at TEXT
            )
        """)

        conn.commit()

        # ----------------------------------------------------
        # ПРОВЕРКА СТАРОЙ БАЗЫ
        # ----------------------------------------------------

        columns = conn.execute(
            "PRAGMA table_info(messages)"
        ).fetchall()

        existing_columns = {
            row["name"]
            for row in columns
        }

        migrations = {

            "chat_id":
                "ALTER TABLE messages ADD COLUMN chat_id INTEGER",

            "message_id":
                "ALTER TABLE messages ADD COLUMN message_id INTEGER",

            "sender_id":
                "ALTER TABLE messages ADD COLUMN sender_id INTEGER",

            "sender_name":
                "ALTER TABLE messages ADD COLUMN sender_name TEXT",

            "sender_username":
                "ALTER TABLE messages ADD COLUMN sender_username TEXT",

            "text":
                "ALTER TABLE messages ADD COLUMN text TEXT",

            "media_type":
                "ALTER TABLE messages ADD COLUMN media_type TEXT",

            "media_name":
                "ALTER TABLE messages ADD COLUMN media_name TEXT",

            "date":
                "ALTER TABLE messages ADD COLUMN date TEXT",

            "is_deleted":
                "ALTER TABLE messages ADD COLUMN is_deleted INTEGER DEFAULT 0",
        }

        for column_name, sql in migrations.items():

            if column_name not in existing_columns:

                print(
                    f"[DB] Добавляю отсутствующий столбец: "
                    f"{column_name}"
                )

                conn.execute(sql)

        conn.commit()

        # ----------------------------------------------------
        # ПРОВЕРКА ТАБЛИЦЫ EDITS
        # ----------------------------------------------------

        edit_columns = conn.execute(
            "PRAGMA table_info(edits)"
        ).fetchall()

        existing_edit_columns = {
            row["name"]
            for row in edit_columns
        }

        edit_migrations = {

            "chat_id":
                "ALTER TABLE edits ADD COLUMN chat_id INTEGER",

            "message_id":
                "ALTER TABLE edits ADD COLUMN message_id INTEGER",

            "old_text":
                "ALTER TABLE edits ADD COLUMN old_text TEXT",

            "new_text":
                "ALTER TABLE edits ADD COLUMN new_text TEXT",

            "edited_at":
                "ALTER TABLE edits ADD COLUMN edited_at TEXT",
        }

        for column_name, sql in edit_migrations.items():

            if column_name not in existing_edit_columns:

                print(
                    f"[DB] Добавляю отсутствующий столбец "
                    f"в edits: {column_name}"
                )

                conn.execute(sql)

        conn.commit()

    print("[DB] База данных готова.")


# ============================================================
# СОХРАНИТЬ СООБЩЕНИЕ
# ============================================================

def save_message(
    chat_id,
    message_id,
    sender_id,
    sender_name,
    sender_username,
    text,
    media_type,
    media_name,
    date
):

    with get_connection() as conn:

        conn.execute("""
            INSERT OR REPLACE INTO messages (
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,

                media_type,
                media_name,

                date,
                is_deleted
            )

            VALUES (
                ?, ?,
                ?, ?, ?,
                ?,
                ?, ?,
                ?,
                0
            )
        """, (
            chat_id,
            message_id,

            sender_id,
            sender_name,
            sender_username,

            text,

            media_type,
            media_name,

            date
        ))

        conn.commit()


# ============================================================
# ПОЛУЧИТЬ ОДНО СООБЩЕНИЕ
# ============================================================

def get_message(
    chat_id,
    message_id
):

    with get_connection() as conn:

        return conn.execute("""
            SELECT
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,

                media_type,
                media_name,

                date,
                is_deleted

            FROM messages

            WHERE chat_id = ?
              AND message_id = ?

            LIMIT 1
        """, (
            chat_id,
            message_id
        )).fetchone()


# ============================================================
# ПОЛУЧИТЬ СООБЩЕНИЯ ПО MESSAGE_ID
#
# ВАЖНО:
# Telegram при удалении может не передать chat_id.
#
# Поэтому ищем только по message_id.
# ============================================================

def get_messages_by_message_id(message_id):

    with get_connection() as conn:

        return conn.execute("""
            SELECT
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,

                media_type,
                media_name,

                date,
                is_deleted

            FROM messages

            WHERE message_id = ?
        """, (
            message_id,
        )).fetchall()


# ============================================================
# ОБНОВИТЬ ТЕКСТ СООБЩЕНИЯ
# ============================================================

def update_message_text(
    chat_id,
    message_id,
    new_text
):

    with get_connection() as conn:

        conn.execute("""
            UPDATE messages

            SET text = ?

            WHERE chat_id = ?
              AND message_id = ?
        """, (
            new_text,
            chat_id,
            message_id
        ))

        conn.commit()


# ============================================================
# СОХРАНИТЬ ИЗМЕНЕНИЕ
# ============================================================

def save_edit(
    chat_id,
    message_id,
    old_text,
    new_text,
    edited_at
):

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO edits (
                chat_id,
                message_id,

                old_text,
                new_text,

                edited_at
            )

            VALUES (
                ?, ?,
                ?, ?,
                ?
            )
        """, (
            chat_id,
            message_id,

            old_text,
            new_text,

            edited_at
        ))

        conn.commit()


# ============================================================
# ПОМЕТИТЬ СООБЩЕНИЕ КАК УДАЛЁННОЕ
# ============================================================

def mark_deleted(
    chat_id,
    message_id
):

    with get_connection() as conn:

        conn.execute("""
            UPDATE messages

            SET is_deleted = 1

            WHERE chat_id = ?
              AND message_id = ?
        """, (
            chat_id,
            message_id
        ))

        conn.commit()


# ============================================================
# ПОЛУЧИТЬ НЕУДАЛЁННЫЕ СООБЩЕНИЯ
# ============================================================

def get_undeleted_messages(limit=100):

    with get_connection() as conn:

        return conn.execute("""
            SELECT
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,

                media_type,
                media_name,

                date,
                is_deleted

            FROM messages

            WHERE is_deleted = 0

            LIMIT ?
        """, (
            limit,
        )).fetchall()


# ============================================================
# ПОЛУЧИТЬ НЕУДАЛЁННЫЕ СООБЩЕНИЯ КОНКРЕТНОГО ЧАТА
# ============================================================

def get_undeleted_messages_for_chat(
    chat_id,
    limit=100
):

    with get_connection() as conn:

        return conn.execute("""
            SELECT
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,

                media_type,
                media_name,

                date,
                is_deleted

            FROM messages

            WHERE chat_id = ?
              AND is_deleted = 0

            LIMIT ?
        """, (
            chat_id,
            limit
        )).fetchall()
