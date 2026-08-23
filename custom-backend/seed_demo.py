from app.database import ensure_demo_users, init_db

if __name__ == "__main__":
    init_db()
    ensure_demo_users()
    print("Demo users and files created.")
