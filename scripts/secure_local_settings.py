"""Replace known local placeholder keys without printing their values."""
import secrets

from dotenv import dotenv_values, set_key

from app.config import BASE_DIR


def main():
    path = BASE_DIR / ".env"
    values = dotenv_values(path)
    defaults = {"SECRET_KEY": {"", "dev-secret", "change-me-for-production"},
                "IOT_API_KEY": {"", "change-me-for-iot-demo"}}
    for key, insecure in defaults.items():
        if values.get(key, "") in insecure:
            set_key(str(path), key, secrets.token_urlsafe(48))
            print("Replaced placeholder:", key)


if __name__ == "__main__":
    main()
