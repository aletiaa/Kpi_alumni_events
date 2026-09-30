"""Private-chat commands backed by the website database, never the legacy JSON files."""
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
from sqlalchemy import func

from app.config import APP_BASE_URL
from app.models import (User, Event, News, ChatLink, Registration, TelegramSubscription,
                        TelegramLink, TelegramBotReply, TelegramUpload)
from app.services.messaging import eligible_user
from app.services.event_registration import register


def button(label, data):
    return {'text':label, 'callback_data':data}


def message(text, rows=None):
    result = {'text':text[:3900]}
    if rows:
        result['reply_markup'] = {'inline_keyboard':rows}
    return result


def website(path, en):
    text = APP_BASE_URL + path
    if urlparse(APP_BASE_URL).hostname in {'localhost', '127.0.0.1', '::1'}:
        text += '\n' + ('This local address works only on the computer running the website.' if en else
                       'Ця локальна адреса працює лише на комп’ютері, де запущено сайт.')
    return message(text)


def private_message(update):
    callback = update.get('callback_query')
    source = callback.get('message', {}) if callback else update.get('message', {})
    sender = callback.get('from', {}) if callback else source.get('from', {})
    chat = source.get('chat', {})
    if chat.get('type') != 'private' or chat.get('id') != sender.get('id') or sender.get('is_bot'):
        return None
    return source, sender, str(chat['id']), callback


def dispatch(db, update):
    parsed = private_message(update)
    if not parsed or not isinstance(update.get('update_id'), int):
        return
    source, sender, chat_id, callback = parsed
    key = 'update:' + str(update['update_id'])
    if db.get(TelegramBotReply, key):
        return
    recent = db.query(TelegramBotReply).filter(TelegramBotReply.chat_id==chat_id,
        TelegramBotReply.created_at > datetime.utcnow()-timedelta(minutes=1)).count()
    if recent >= 30:
        return
    sub = db.query(TelegramSubscription).filter_by(chat_id=chat_id, revoked_at=None).first()
    user = db.get(User, sub.user_id) if sub else None
    if not eligible_user(user):
        user = None
    en = (user.preferred_language == 'en') if user else sender.get('language_code', '').startswith('en')
    t = lambda uk, english: english if en else uk
    data = callback.get('data', '') if callback else source.get('text', '')
    if not isinstance(data, str):
        data = ''
    command = data.split()[0].split('@')[0].lstrip('/') if data.strip() else ''
    admin_link = db.query(TelegramLink).filter_by(chat_id=chat_id).first()
    is_admin = False
    if admin_link:
        from app.services.admin_csv import find_admin_by_email
        try:
            is_admin = bool(find_admin_by_email(admin_link.admin_email))
        except OSError:
            pass
    method = 'sendMessage'
    payload = message(t('Пов’яжіть профіль на сайті: ', 'Link your website profile: ') + APP_BASE_URL + '/profile/telegram')
    if command in {'start', 'menu', 'help'}:
        rows = [[button(t('Події','Events'),'events'), button(t('Новини','News'),'news')],
                [button(t('Мій профіль','My profile'),'profile'), button(t('Мої події','My events'),'my_events')],
                [button(t('Чати','Chats'),'chats'), button(t('Мої файли','My files'),'files')],
                [button(t('Надіслати файл','Submit a file'),'upload'), button(t('Налаштування','Settings'),'settings')],
                [button(t('Повідомлення','Messages'),'messages'), button(t('Опитування','Surveys'),'surveys')],
                [button(t('Реєстрація / вхід','Register / log in'),'login')]]
        if is_admin:
            rows.append([button(t('Адміністрування','Administration'),'admin')])
        payload = message(t('AlumnixHub — меню випускника', 'AlumnixHub — alumni menu') + '\n' +
            (t('Профіль підключено.', 'Profile linked.') if user else t('Акаунт адміністратора підключено.', 'Administrator account linked.') if is_admin else
             t('Увійдіть на сайт і підключіть Telegram у профілі.', 'Sign in on the website and connect Telegram in your profile.')), rows)
    elif command == 'stop':
        payload = message(t('Telegram відключено. Підписки скасовано.', 'Telegram disconnected. Subscriptions cancelled.'))
    elif command in {'login','register'}:
        payload = website('/register' if command == 'register' else '/login', en)
    elif command == 'admin' and is_admin:
        payload = message(t('Керування на сайті (потрібен вхід адміністратора):', 'Website administration (admin sign-in required):'), [
            [button(t('Новини','News'),'admin_news'),button(t('Події','Events'),'admin_events')],
            [button(t('Користувачі','Users'),'admin_users'),button(t('Чати','Chats'),'admin_chats')],
            [button(t('Розсилки','Broadcasts'),'admin_bots'),button(t('Файли','Files'),'admin_files')]])
    elif command.startswith('admin_') and is_admin:
        path = {'admin_news':'/admin/news','admin_events':'/admin/events','admin_users':'/admin/users',
                'admin_chats':'/admin/chats','admin_bots':'/admin/bots','admin_files':'/admin/bots/files'}.get(command)
        if path:
            payload = website(path, en)
    elif user:
        parts = command.split(':')
        action = parts[0]
        number = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) < 10 else 0
        if action in {'events','news','my_events','chats','files'}:
            page = min(number, 1000)
            if action in {'events', 'my_events'}:
                query = db.query(Event).filter(Event.start_time > datetime.utcnow())
                if action == 'my_events':
                    query = query.join(Registration).filter(Registration.user_id == user.id)
                rows = query.order_by(Event.start_time, Event.id).offset(page*5).limit(6).all()
                buttons = [[button(e.title[:60], 'event:'+str(e.id))] for e in rows[:5]]
            elif action == 'news':
                rows = db.query(News).filter_by(is_published=True).order_by(News.created_at.desc(), News.id.desc()).offset(page*5).limit(6).all()
                buttons = [[button(n.title[:60], 'article:'+str(n.id))] for n in rows[:5]]
            elif action == 'files':
                rows = db.query(TelegramUpload).filter_by(user_id=user.id).order_by(TelegramUpload.id.desc()).offset(page*5).limit(6).all()
                buttons = [[button(f.filename[:60], 'file:'+str(f.id))] for f in rows[:5]]
            else:
                query = db.query(ChatLink).filter_by(is_active=True)
                for field in ('faculty','specialty','group_name','graduation_year'):
                    column = getattr(ChatLink, field)
                    query = query.filter((column.is_(None)) | (column == getattr(user, field)))
                rows = query.order_by(ChatLink.id).offset(page*5).limit(6).all()
                buttons = [[{'text':c.title[:60], 'url':c.url}] for c in rows[:5]
                           if urlparse(c.url).scheme in {'http','https'}]
            nav = []
            if page: nav.append(button(t('Назад','Previous'),f'{action}:{page-1}'))
            if len(rows)>5: nav.append(button(t('Далі','Next'),f'{action}:{page+1}'))
            if nav: buttons.append(nav)
            buttons.append([button(t('Меню','Menu'),'menu')])
            payload = message(t('Оберіть запис:','Select an item:') if rows else t('Записів немає.','No items found.'), buttons)
        elif action in {'event','join','leave'} and number:
            event = db.get(Event, number)
            if event:
                if action == 'join':
                    result = register(db, user, number)
                    labels = {'registered':('Ви зареєстровані.','You are registered.'),
                              'already_registered':('Ви вже зареєстровані.','You are already registered.'),
                              'full':('Вільних місць немає.','The event is full.'),
                              'deadline_passed':('Реєстрацію закрито.','Registration is closed.')}
                    payload = message(t(*labels.get(result, ('Реєстрація недоступна.','Registration unavailable.'))))
                elif action == 'leave':
                    db.query(Registration).filter_by(user_id=user.id,event_id=number).delete()
                    payload = message(t('Реєстрацію скасовано.','Registration cancelled.'))
                else:
                    registered = db.query(Registration.id).filter_by(user_id=user.id,event_id=number).first()
                    label, target = (t('Скасувати реєстрацію','Cancel registration'),'leave') if registered else (t('Підтвердити реєстрацію','Confirm registration'),'join')
                    payload = message(f'{event.title}\n{event.start_time:%d.%m.%Y %H:%M} UTC\n{event.location}\n\n{event.description or ""}', [[button(label, f'{target}:{number}')]])
            else: payload = message(t('Подію не знайдено.','Event not found.'))
        elif action == 'article' and number:
            article = db.query(News).filter_by(id=number,is_published=True).first()
            payload = message(article.title+'\n\n'+article.content) if article else message(t('Новину не знайдено.','Article not found.'))
        elif action == 'profile':
            payload = message('\n'.join(filter(None,[user.full_name, user.faculty, user.specialty, user.group_name, user.bio]))[:3500], [[button(t('Редагувати на сайті','Edit on website'),'edit_profile')]])
        elif action in {'settings','edit_profile','messages','surveys'}:
            payload = website({'settings':'/profile/telegram','edit_profile':'/profile','messages':'/messages','surveys':'/surveys'}[action], en)
        elif action == 'upload':
            payload = message(t('Надішліть фото, відео або документ до 20 МБ. Матеріали доступні вам та адміністраторам. Не надсилайте конфіденційні документи.',
                                'Send a photo, video or document up to 20 MB. Files are available to you and administrators. Do not send confidential documents.'))
        elif action == 'file' and number:
            upload = db.query(TelegramUpload).filter_by(id=number,user_id=user.id).first()
            if upload:
                method = {'photo':'sendPhoto','video':'sendVideo','document':'sendDocument'}[upload.kind]
                payload = {upload.kind:upload.file_id}
            else: payload = message(t('Файл не знайдено.','File not found.'))
        elif not callback and any(k in source for k in ('photo','video','document')):
            kind = next(k for k in ('photo','video','document') if k in source)
            file = source[kind][-1] if kind == 'photo' else source[kind]
            size = file.get('file_size', 0)
            recent = db.query(TelegramUpload).filter(TelegramUpload.user_id==user.id,
                TelegramUpload.created_at > datetime.utcnow()-timedelta(hours=1)).count()
            if size > 20*1024*1024 or recent >= 10:
                payload = message(t('Ліміт: 20 МБ на файл, 10 файлів на годину.','Limit: 20 MB per file, 10 files per hour.'))
            elif file.get('file_id'):
                db.add(TelegramUpload(user_id=user.id,update_id=update['update_id'],file_id=file['file_id'],
                    kind=kind,filename=(file.get('file_name') or kind)[:255],size=size))
                payload = message(t('Файл збережено для перегляду адміністраторами.','File saved for administrator review.'))
        else:
            payload = message(t('Скористайтеся /menu.','Use /menu.'))
    payload['chat_id'] = chat_id
    db.add(TelegramBotReply(key=key,chat_id=chat_id,user_id=user.id if user else None,
                           method=method,payload=json.dumps(payload,ensure_ascii=False)))
