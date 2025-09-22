import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "app.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
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
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country_code TEXT DEFAULT 'unknown'
        )
    """)

    # Domain mappings table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS domain_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            chatbot_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (client_id)
        )
    """)

    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_client_session ON chats(client_id, session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain_mappings_domain ON domain_mappings(domain)")

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def register_domain(domain, client_id):
    """Register a domain for a specific client"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get chatbot_key for the client
        cursor.execute("SELECT chatbot_key FROM users WHERE client_id = ?", (client_id,))
        user = cursor.fetchone()

        if not user or not user['chatbot_key']:
            return False

        # Clean domain
        clean_domain = domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')

        # Insert domain mapping
        cursor.execute("""
            INSERT OR REPLACE INTO domain_mappings (domain, client_id, chatbot_key)
            VALUES (?, ?, ?)
        """, (clean_domain, client_id, user['chatbot_key']))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error registering domain: {e}")
        return False
    finally:
        conn.close()

def remove_domain(domain: str, client_id: str) -> bool:
    """
    Remove a domain mapping for a client.
    Returns True if a row was deleted, False otherwise.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM domain_mappings WHERE domain=? AND client_id=?",
            (domain.lower().strip(), client_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_client_by_domain(domain):
    """Get client information by domain"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Clean the domain
        clean_domain = domain.lower().replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')
        print(f"Looking up domain: '{clean_domain}'")  # Debug

        cursor.execute("""
            SELECT dm.client_id, dm.chatbot_key, u.name as client_name
            FROM domain_mappings dm
            JOIN users u ON dm.client_id = u.client_id
            WHERE dm.domain = ?
        """, (clean_domain,))

        result = cursor.fetchone()
        print(f"Query result: {result}")  # Debug

        return dict(result) if result else None

    except Exception as e:
        print(f"Error looking up domain: {e}")
        return None
    finally:
        conn.close()
# Initialize DB when module is imported
init_db()
