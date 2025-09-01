import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table (clients + admins)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            email TEXT,
            mobile TEXT,
            role TEXT DEFAULT 'client',
            client_id TEXT UNIQUE NOT NULL,
            chatbot_key TEXT
        )
    """)

    # Chats table (per client, per user session)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,         /* "user" or "assistant" */
            message TEXT NOT NULL,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# ✅ Initialize DB when server starts
init_db()
