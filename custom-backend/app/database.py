import os
import sqlite3
from pathlib import Path

import bcrypt

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = DATA_DIR / "app.db"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_user(email: str, password: str, name: str = "") -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email.lower().strip(),),
        )
        if cursor.fetchone():
            raise ValueError("Email already registered")

        user_id = f"usr_{os.urandom(6).hex()}"
        now = __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z"
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, name or email.split("@")[0], email.lower().strip(), hash_password(password), now),
        )
        conn.commit()
        return {"id": user_id, "name": name or email.split("@")[0], "email": email.lower().strip()}
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_file_record(user_id: str, file_name: str, mime_type: str, file_path: str) -> dict:
    conn = get_connection()
    file_id = f"file_{os.urandom(6).hex()}"
    timestamp = __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z"
    size_bytes = os.path.getsize(file_path)
    conn.execute(
        "INSERT INTO files (id, user_id, file_name, mime_type, size_bytes, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, user_id, file_name, mime_type, size_bytes, file_path, timestamp),
    )
    conn.commit()
    conn.close()
    return {
        "id": file_id,
        "user_id": user_id,
        "file_name": file_name,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "file_path": file_path,
        "uploaded_at": timestamp,
    }


def list_files_for_user(user_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM files WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_file_by_id(file_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM files WHERE id = ?",
        (file_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_file_by_name(user_id: str, file_name: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM files WHERE user_id = ? AND file_name = ?",
        (user_id, file_name),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def ensure_demo_users() -> None:
    conn = get_connection()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    demo_users = [
        {"email": "alice@example.com", "password": "Password123!", "name": "Alice Nakamura"},
        {"email": "bob@example.com", "password": "Password123!", "name": "Bob Alvarez"},
        {"email": "carol@example.com", "password": "Password123!", "name": "Carol Whitfield"},
    ]

    if user_count == 0:
        for user in demo_users:
            created = create_user(user["email"], user["password"], user["name"])
            user_dir = STORAGE_DIR / created["id"]
            user_dir.mkdir(parents=True, exist_ok=True)
            seed_files = [
                ("resume.txt", "This is Alice's resume.", "text/plain"),
                ("profile_photo.txt", "This is Alice's photo placeholder.", "text/plain"),
            ] if user["email"] == "alice@example.com" else [
                ("notes.txt", f"This is {user['name']}'s notes.", "text/plain"),
                ("invoice.txt", f"This is {user['name']}'s invoice.", "text/plain"),
            ]
            for item in seed_files:
                file_path = user_dir / item[0]
                file_path.write_text(item[1], encoding="utf-8")
                create_file_record(created["id"], item[0], item[2], str(file_path))

    extra_files = {
        "alice@example.com": ("alice_notes.txt", "text/plain", "Confidential notes for Alice's FOSSEE project.\n"),
        "bob@example.com": ("bob_notes.txt", "text/plain", "Confidential notes for Bob FOSSEE project.\n"),
        "carol@example.com": ("carol_notes.txt", "text/plain", "Confidential notes for Carol FOSSEE project.\n"),
    }
    for email, (file_name, mime_type, content) in extra_files.items():
        user = get_user_by_email(email)
        if not user or get_file_by_name(user["id"], file_name):
            continue
        user_dir = STORAGE_DIR / user["id"]
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / file_name
        file_path.write_text(content, encoding="utf-8")
        create_file_record(user["id"], file_name, mime_type, str(file_path))
