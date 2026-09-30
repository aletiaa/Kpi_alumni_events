from itsdangerous import BadSignature, URLSafeTimedSerializer
from fastapi import HTTPException

from app.config import SECRET_KEY

signer = URLSafeTimedSerializer(SECRET_KEY, salt="direct-message")


def eligible_user(user):
    return bool(user and user.is_active and user.is_email_verified and not user.is_blocked)


def can_start_conversation(current, recipient):
    return bool(eligible_user(current) and eligible_user(recipient)
                and current.id != recipient.id and recipient.is_profile_public)


def message_token(sender_id, recipient_id):
    return signer.dumps([sender_id, recipient_id])


def verify_message_token(token, sender_id, recipient_id):
    try:
        if signer.loads(token, max_age=7200) != [sender_id, recipient_id]:
            raise BadSignature("Wrong conversation")
    except BadSignature:
        raise HTTPException(403, "Оновіть сторінку та повторіть дію.")
