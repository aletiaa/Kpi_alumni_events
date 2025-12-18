from sqlalchemy import text
from app.db import engine

def main():
    with engine.begin() as conn:
        # registrations depend on events -> delete registrations first
        conn.execute(text("TRUNCATE TABLE registrations RESTART IDENTITY CASCADE;"))
        conn.execute(text("TRUNCATE TABLE events RESTART IDENTITY CASCADE;"))
    print("OK: events + registrations cleared")

if __name__ == "__main__":
    main()
