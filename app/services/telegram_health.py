from datetime import datetime, timedelta
from app.config import TELEGRAM_ENABLED
from app.models import TelegramState


def health(request, db):
    state = db.get(TelegramState, 1)
    tasks = getattr(request.app.state, 'telegram_tasks', [])
    workers = len(tasks) == 3 and all(not task.done() for task in tasks)
    recent = bool(state and state.checked_at and state.checked_at > datetime.utcnow()-timedelta(seconds=90))
    return {'online':bool(TELEGRAM_ENABLED and workers and recent and state.status=='connected'),
            'username':state.bot_username if state else None}
