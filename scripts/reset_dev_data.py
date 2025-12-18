from sqlalchemy import text
from app.db import engine

def main():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE registrations RESTART IDENTITY CASCADE;"))
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
    print("OK: users and registrations cleared")

if __name__ == "__main__":
    main()

