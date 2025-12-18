from dotenv import load_dotenv
load_dotenv()

from app.services.emailer import send_verification_email

def main():
    send_verification_email(
        "alina.seikauskaite2@gmail.com",
        "http://127.0.0.1:8000/verify?token=TEST"
    )
    print("OK: email function executed")

if __name__ == "__main__":
    main()
