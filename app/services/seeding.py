# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    ChatLink,
    DirectMessage,
    Event,
    EventComment,
    EventReaction,
    News,
    Registration,
    Survey,
    SurveyAnswer,
    SurveyQuestion,
    User,
)
from app.security import hash_password

DEFAULT_EVENT_IMAGE = "/static/img/kpi-main.png"
EVENT_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1523580846011-d3a5bc25702b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1517048676732-d65bc937f952?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1556761175-b413da4baf72?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1556761175-4b46a572b786?auto=format&fit=crop&w=1200&q=80",
]
NEWS_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1503428593586-e225b39bddfe?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1200&q=80",
]
USER_AVATARS = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=400&q=80",
]
USER_STATUSES = ["Backend Engineer", "Cybersecurity Mentor", "Student Coordinator", "Frontend Engineer", "Looking for Internship", "Data Engineer", "Product Manager", "Security Student", "Private Guest"]
USER_POSITIONS = ["Backend Engineer", "Cybersecurity Consultant", "Student Community Lead", "Frontend Engineer", "QA Intern", "Data Engineer", "Product Manager", "Security Analyst", "Guest"]
USER_COMPANIES = ["SoftServe", "Ajax Systems", "KPI Student Council", "EPAM", "Genesis", "DataArt", "Grammarly", "MacPaw", ""]
USER_LOCATIONS = ["Україна, Київ", "Польща, Варшава", "Україна, Київ", "Німеччина, Берлін", "Україна, Львів", "Україна, Київ", "Чехія, Прага", "Україна, Харків", ""]
USER_SKILLS = [
    "Python, FastAPI, PostgreSQL, REST API",
    "Cybersecurity, SOC, CTF, incident response",
    "Community management, surveys, event coordination",
    "React, TypeScript, UX, accessibility",
    "QA basics, test cases, English interview prep",
    "SQL, ETL, cloud data pipelines, dashboards",
    "Product discovery, roadmap, analytics, interviews",
    "Network security, Linux, cloud security",
    "",
]
USER_HELP_TOPICS = [
    "Портфоліо, перший backend-проєкт, співбесіди",
    "Кібербезпека, CTF, підготовка до junior security ролі",
    "Організація подій, студентські ініціативи",
    "Frontend roadmap, pet-проєкти, code review",
    "Пошук стажування, резюме, перша співбесіда",
    "Data engineering, SQL, аналітичне портфоліо",
    "Product thinking, discovery, user interviews",
    "Безпека інфраструктури, Linux, лабораторні проєкти",
    "",
]
DEMO_COMMENT_BODIES = [
    "Дуже чекаю на цю зустріч, особливо на Q&A з випускниками.",
    "Було б цікаво почути більше про реальні кейси з індустрії.",
    "Планую долучитися і запросити одногрупників.",
    "Тема корисна для студентів, які шукають перший досвід.",
    "Хочу поставити питання про менторство та кар'єрний перехід.",
    "Класний формат, такі події добре об'єднують спільноту.",
]
STOCK_SOURCES = [
    "https://www.shutterstock.com/search/university-events?dd_referrer=https%3A%2F%2Fwww.google.com%2F",
    "https://www.gettyimages.com/photos/university-event",
    "https://www.magnific.com/free-photos-vectors/university-event",
]


def seed_events_if_empty(db: Session) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def event(title, short, desc, location, days, hour, duration, capacity):
        start = now + timedelta(days=days, hours=hour)
        return {
            "title": title,
            "short_description": short,
            "description": desc,
            "location": location,
            "start_time": start,
            "end_time": start + timedelta(hours=duration),
            "registration_deadline": start - timedelta(hours=6),
            "capacity": capacity,
            "image_url": DEFAULT_EVENT_IMAGE,
        }

    rows = [
        event("Зустріч випускників КПІ", "Нетворкінг випускників, студентів і викладачів.", "Вечір знайомств, історій успіху та пошуку менторів для студентських команд.", "Головний корпус КПІ", 2, 18, 3, 180),
        event("Майстерня AI та NLP", "Практична сесія з рекомендацій, класифікації текстів і FastAPI.", "Випускники з IT-компаній покажуть, як будувати прості ML-сервіси для університетських платформ.", "КПІ, IT-центр", 5, 16, 2, 80),
        event("Кар'єрна лекція: Data Analytics", "Портфоліо, співбесіди та перша аналітична роль.", "Випускники діляться досвідом роботи з даними, BI та фінансовою аналітикою.", "Аудиторія 304", 7, 17, 2, 120),
        event("Startup Pitch Evening", "Студентські стартапи презентують ідеї перед менторами.", "Команди отримають фідбек щодо продукту, бізнес-моделі та технічної реалізації.", "Sikorsky Challenge Hub", 9, 18, 3, 150),
        event("Основи кібербезпеки", "Фішинг, MFA, паролі та цифрова гігієна.", "Практичний воркшоп для студентів і молодих випускників про персональну кібербезпеку.", "Корпус 18, ауд. 214", 11, 15, 2, 90),
        event("IoT Demo Day", "Демонстрація сенсорного підрахунку відвідувачів подій.", "Показ роботи IoT-модуля, API та панелі статистики відвідуваності.", "Лабораторія A1", 13, 14, 2, 60),
        event("Архітектура веб-сервісів", "FastAPI, PostgreSQL, деплой і підтримка навчальних систем.", "Гостьова лекція про масштабування web-сервісів і прості архітектурні рішення для MVP.", "Онлайн", 15, 19, 2, 500),
        event("Ярмарок волонтерських проєктів", "Студентські й alumni-ініціативи шукають волонтерів.", "Команди презентують соціальні, освітні й технічні проєкти, до яких можна долучитися.", "Площа знань КПІ", 22, 12, 4, 300),
        event("Mentor Speed Dating", "Короткі розмови студентів з менторами зі свого напряму.", "Формат швидких знайомств допоможе знайти наставника, команду або тему дипломної роботи.", "Бібліотека КПІ", 24, 17, 2, 120),
        event("Alumni Product Night", "Продуктові кейси від випускників КПІ.", "PM-и та дизайнери розкажуть, як валідувати ідеї й працювати з користувацьким фідбеком.", "CLUST Space", 28, 18, 3, 100),
        event("Python для автоматизації", "Скрипти, API та маленькі інструменти для щоденної роботи.", "Практичний воркшоп для студентів, які хочуть автоматизувати рутинні задачі.", "Корпус 12", 31, 16, 2, 70),
        event("Фінанси для інженерів", "Бюджет, податки, ФОП і фінансове планування.", "Випускники розкажуть про базові фінансові рішення на старті кар'єри.", "Аудиторія 101", 35, 18, 2, 110),
    ]

    for index, row in enumerate(rows):
        row["image_url"] = EVENT_IMAGE_URLS[index % len(EVENT_IMAGE_URLS)]

    inserted = 0
    for row in rows:
        item = db.query(Event).filter(Event.title == row["title"]).first()
        if item:
            continue
        db.add(Event(**row))
        inserted += 1
    db.commit()
    for index, existing_event in enumerate(db.query(Event).order_by(Event.id.asc()).all()):
        if not existing_event.image_url or existing_event.image_url == DEFAULT_EVENT_IMAGE:
            existing_event.image_url = EVENT_IMAGE_URLS[index % len(EVENT_IMAGE_URLS)]
        if not existing_event.image_source_url:
            existing_event.image_source_url = STOCK_SOURCES[index % len(STOCK_SOURCES)]
    db.commit()
    return inserted


def _add_user_if_missing(db: Session, **kwargs) -> bool:
    if db.query(User).filter(User.email == kwargs["email"]).first():
        return False
    kwargs.setdefault("password_hash", hash_password("demo12345"))
    kwargs.setdefault("is_active", True)
    kwargs.setdefault("is_email_verified", True)
    kwargs.setdefault("is_profile_public", True)
    db.add(User(**kwargs))
    return True


def seed_demo_content_if_empty(db: Session) -> dict[str, int]:
    inserted = {"users": 0, "news": 0, "chats": 0, "surveys": 0, "registrations": 0, "iot": 0, "reactions": 0, "comments": 0, "messages": 0}

    users = [
        dict(full_name="Олена Коваль", email="olena.alumni@example.com", role="alumni", faculty="ФІОТ", specialty="Інженерія програмного забезпечення", group_name="ІП-91", graduation_year=2023, bio="Backend-розробниця, допомагає студентам з FastAPI та базами даних.", telegram_username="@olena_kpi", linkedin_url="https://www.linkedin.com/in/demo-olena", avatar_url=USER_AVATARS[0], status=USER_STATUSES[0], preferred_language="uk", notifications_enabled=True),
        dict(full_name="Андрій Мельник", email="andrii.alumni@example.com", role="alumni", faculty="ФЕЛ", specialty="Кібербезпека", group_name="КБ-82", graduation_year=2022, bio="Проводить відкриті лекції з кібербезпеки для студентів.", telegram_username="@andrii_security", linkedin_url="https://www.linkedin.com/in/demo-andrii", avatar_url=USER_AVATARS[1], status=USER_STATUSES[1], preferred_language="uk", notifications_enabled=True),
        dict(full_name="Марія Шевченко", email="maria.student@example.com", role="student", faculty="ФММ", specialty="Менеджмент", group_name="УВ-11", graduation_year=2027, bio="Координує студентські опитування та комунікацію з випускниками.", telegram_username="@maria_kpi"),
        dict(full_name="Ігор Петренко", email="ihor.ip91@example.com", role="alumni", faculty="ФІОТ", specialty="Інженерія програмного забезпечення", group_name="ІП-91", graduation_year=2023, bio="Frontend engineer, відкритий до менторства для ІП-91.", telegram_username="@ihor_frontend"),
        dict(full_name="Софія Литвин", email="sofia.ip91@example.com", role="student", faculty="ФІОТ", specialty="Інженерія програмного забезпечення", group_name="ІП-91", graduation_year=2023, bio="Шукає команду для pet-проєкту та стажування.", telegram_username="@sofia_code"),
        dict(full_name="Дмитро Гончар", email="dmytro.fiot@example.com", role="alumni", faculty="ФІОТ", specialty="Комп'ютерні науки", group_name="КН-01", graduation_year=2024, bio="Data engineer, допомагає з ETL і хмарними сервісами.", telegram_username="@dmytro_data"),
        dict(full_name="Катерина Романюк", email="kateryna.fmm@example.com", role="alumni", faculty="ФММ", specialty="Менеджмент", group_name="УВ-11", graduation_year=2027, bio="Організовує career talks і менторські зустрічі.", telegram_username="@kateryna_pm"),
        dict(full_name="Назар Бойко", email="nazar.cyber@example.com", role="student", faculty="ФЕЛ", specialty="Кібербезпека", group_name="КБ-82", graduation_year=2022, bio="Цікавиться SOC, CTF і захистом інфраструктури.", telegram_username="@nazar_sec"),
        dict(full_name="Приватний Користувач", email="private@example.com", role="guest", faculty="ФІОТ", specialty="Комп'ютерні науки", group_name="ІП-01", is_profile_public=False),
    ]
    for row in users:
        if _add_user_if_missing(db, **row):
            inserted["users"] += 1
    db.commit()
    for index, user in enumerate(db.query(User).order_by(User.id.asc()).all()):
        if not user.avatar_url:
            user.avatar_url = USER_AVATARS[index % len(USER_AVATARS)]
        if not user.status:
            user.status = USER_STATUSES[index % len(USER_STATUSES)]
        if not user.current_position:
            user.current_position = USER_POSITIONS[index % len(USER_POSITIONS)]
        if not user.company:
            user.company = USER_COMPANIES[index % len(USER_COMPANIES)]
        if not user.city_country:
            user.city_country = USER_LOCATIONS[index % len(USER_LOCATIONS)]
        if not user.skills:
            user.skills = USER_SKILLS[index % len(USER_SKILLS)]
        if not user.help_topics:
            user.help_topics = USER_HELP_TOPICS[index % len(USER_HELP_TOPICS)]
        if user.role == "alumni" and index % 2 == 0:
            user.is_mentor = True
            if not user.mentorship_topics:
                user.mentorship_topics = USER_HELP_TOPICS[index % len(USER_HELP_TOPICS)]
        if not user.preferred_language:
            user.preferred_language = "uk"
    db.commit()
    if db.query(News).count() < 5:
        existing = {n.title for n in db.query(News).all()}
        items = [
            News(title="Платформа alumni-спільноти КПІ запущена в демо-режимі", image_url=DEFAULT_EVENT_IMAGE, image_source_url=STOCK_SOURCES[0], short_description="Єдиний простір для новин, подій, контактів, чатів та опитувань.", content="Система допомагає адміністраторам підтримувати зв'язок із випускниками, а студентам знаходити менторів, події та корисні спільноти.", is_published=True),
            News(title="Випускники проведуть серію кар'єрних зустрічей", image_url=DEFAULT_EVENT_IMAGE, image_source_url=STOCK_SOURCES[0], short_description="Стартує цикл лекцій про IT, менеджмент, кібербезпеку та аналітику.", content="Кожна зустріч міститиме коротку лекцію, Q&A та нетворкінг. Реєстрація доступна на сторінці подій.", is_published=True),
            News(title="Опитування щодо розвитку alumni-клубу", image_url=DEFAULT_EVENT_IMAGE, image_source_url=STOCK_SOURCES[0], short_description="Адміністрація збирає ідеї для нових форматів комунікації.", content="Заповніть коротке опитування у відповідному розділі платформи.", is_published=True),
            News(title="Запущено внутрішні повідомлення між потоками", image_url=DEFAULT_EVENT_IMAGE, image_source_url=STOCK_SOURCES[0], short_description="Користувачі одного потоку можуть писати одне одному просто на сайті.", content="Це допомагає студентам швидше знаходити випускників зі своєї групи, факультету або року випуску.", is_published=True),
            News(title="Події отримали реакції та коментарі", image_url=DEFAULT_EVENT_IMAGE, image_source_url=STOCK_SOURCES[0], short_description="Зареєстровані учасники можуть залишати фідбек до подій.", content="Лайки, дизлайки та коментарі допомагають адміністраторам бачити інтерес спільноти.", is_published=True),
        ]
        db.add_all([item for item in items if item.title not in existing])
        inserted["news"] += len([item for item in items if item.title not in existing])
        db.commit()

    for index, news_item in enumerate(db.query(News).order_by(News.id.asc()).all()):
        if not news_item.image_url or news_item.image_url == DEFAULT_EVENT_IMAGE:
            news_item.image_url = NEWS_IMAGE_URLS[index % len(NEWS_IMAGE_URLS)]
        if not news_item.image_source_url:
            news_item.image_source_url = STOCK_SOURCES[index % len(STOCK_SOURCES)]
    db.commit()
    if db.query(ChatLink).count() < 5:
        existing = {c.title for c in db.query(ChatLink).all()}
        links = [
            ChatLink(title="Загальний alumni-чат КПІ", description="Новини, події та швидкі оголошення для всієї спільноти.", url="https://t.me/kpi_alumni_demo", is_active=True),
            ChatLink(title="ФІОТ: випускники та студенти", description="Пошук менторів, стажувань і технічних консультацій.", url="https://t.me/fiot_alumni_demo", faculty="ФІОТ", specialty="Інженерія програмного забезпечення", group_name="ІП", is_active=True),
            ChatLink(title="Кар'єрні можливості КПІ", description="Вакансії, стажування та анонси партнерських програм.", url="https://www.linkedin.com/school/demo-kpi-alumni/", is_active=True),
            ChatLink(title="ІП-91 потік", description="Окремий чат для потоку ІП-91.", url="https://t.me/ip91_demo", faculty="ФІОТ", group_name="ІП-91", graduation_year=2023, is_active=True),
            ChatLink(title="Кібербезпека КПІ", description="CTF, SOC, безпека застосунків і навчальні матеріали.", url="https://t.me/kpi_cyber_demo", faculty="ФЕЛ", specialty="Кібербезпека", is_active=True),
        ]
        db.add_all([link for link in links if link.title not in existing])
        inserted["chats"] += len([link for link in links if link.title not in existing])
        db.commit()

    if not db.query(Survey).filter(Survey.title == "Потреби alumni-спільноти").first():
        survey = Survey(title="Потреби alumni-спільноти", description="Допоможіть визначити, які сервіси та події потрібні випускникам і студентам.", is_active=True)
        db.add(survey)
        db.commit()
        db.refresh(survey)
        questions = [
            SurveyQuestion(survey_id=survey.id, question_text="У якій країні ви зараз проживаєте?", question_type="text"),
            SurveyQuestion(survey_id=survey.id, question_text="Який ваш поточний статус зайнятості?", question_type="single_choice", options_text="Працюю повний день\nПрацюю частково\nНавчаюся\nШукаю роботу\nПідприємець/підприємиця\nІнше"),
            SurveyQuestion(survey_id=survey.id, question_text="У якій сфері ви зараз працюєте або плануєте працювати?", question_type="single_choice", options_text="IT / Software\nData / AI\nКібербезпека\nІнженерія\nМенеджмент / Бізнес\nОсвіта / Наука\nДержавний сектор\nІнше"),
            SurveyQuestion(survey_id=survey.id, question_text="Який рівень вашого кар'єрного розвитку зараз?", question_type="single_choice", options_text="Студент/студентка\nJunior\nMiddle\nSenior\nLead / Manager\nFounder / Entrepreneur\nЗмінюю сферу"),
            SurveyQuestion(survey_id=survey.id, question_text="Що найбільше допоможе вашому кар'єрному росту?", question_type="single_choice", options_text="Менторство\nНетворкінг\nВакансії та стажування\nТехнічні воркшопи\nКар'єрні консультації\nПублічні виступи випускників"),
            SurveyQuestion(survey_id=survey.id, question_text="Чи готові ви менторити студентів або молодших випускників?", question_type="single_choice", options_text="Так, регулярно\nТак, іноді\nМожливо пізніше\nНі"),
            SurveyQuestion(survey_id=survey.id, question_text="Які теми подій або сервісів варто додати до платформи?", question_type="text"),
        ]
        db.add_all(questions)
        db.commit()
        inserted["surveys"] = 1

    survey = db.query(Survey).filter(Survey.title == "Потреби alumni-спільноти").first()
    if survey:
        wanted_questions = [
            ("У якій країні ви зараз проживаєте?", "text", None),
            ("Який ваш поточний статус зайнятості?", "single_choice", "Працюю повний день\nПрацюю частково\nНавчаюся\nШукаю роботу\nПідприємець/підприємиця\nІнше"),
            ("У якій сфері ви зараз працюєте або плануєте працювати?", "single_choice", "IT / Software\nData / AI\nКібербезпека\nІнженерія\nМенеджмент / Бізнес\nОсвіта / Наука\nДержавний сектор\nІнше"),
            ("Який рівень вашого кар'єрного розвитку зараз?", "single_choice", "Студент/студентка\nJunior\nMiddle\nSenior\nLead / Manager\nFounder / Entrepreneur\nЗмінюю сферу"),
            ("Що найбільше допоможе вашому кар'єрному росту?", "single_choice", "Менторство\nНетворкінг\nВакансії та стажування\nТехнічні воркшопи\nКар'єрні консультації\nПублічні виступи випускників"),
            ("Чи готові ви менторити студентів або молодших випускників?", "single_choice", "Так, регулярно\nТак, іноді\nМожливо пізніше\nНі"),
            ("Які теми подій або сервісів варто додати до платформи?", "text", None),
        ]
        existing_questions = {q.question_text for q in db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).all()}
        for text_value, qtype, options in wanted_questions:
            if text_value not in existing_questions:
                db.add(SurveyQuestion(survey_id=survey.id, question_text=text_value, question_type=qtype, options_text=options))
        db.commit()
    users_for_regs = db.query(User).filter(User.role.in_(["student", "alumni"])).order_by(User.id.asc()).limit(8).all()
    events = db.query(Event).order_by(Event.start_time.asc()).limit(6).all()
    for index, user in enumerate(users_for_regs):
        for event in events[: max(1, min(len(events), (index % 3) + 1))]:
            if not db.query(Registration).filter(Registration.user_id == user.id, Registration.event_id == event.id).first():
                db.add(Registration(user_id=user.id, event_id=event.id))
                inserted["registrations"] += 1
    db.commit()

    registrations = db.query(Registration).limit(20).all()
    for reg in registrations:
        if not db.query(EventReaction).filter(EventReaction.user_id == reg.user_id, EventReaction.event_id == reg.event_id).first():
            db.add(EventReaction(user_id=reg.user_id, event_id=reg.event_id, reaction="like" if reg.id % 4 else "dislike"))
            inserted["reactions"] += 1
        if reg.id % 2 == 0 and not db.query(EventComment).filter(EventComment.user_id == reg.user_id, EventComment.event_id == reg.event_id).first():
            db.add(EventComment(user_id=reg.user_id, event_id=reg.event_id, body=DEMO_COMMENT_BODIES[reg.id % len(DEMO_COMMENT_BODIES)]))
            inserted["comments"] += 1
    db.commit()

    olena = db.query(User).filter(User.email == "olena.alumni@example.com").first()
    ihor = db.query(User).filter(User.email == "ihor.ip91@example.com").first()
    sofia = db.query(User).filter(User.email == "sofia.ip91@example.com").first()
    pairs = [(olena, ihor, "Привіт! Бачу, ми з ІП-91. Можемо обговорити менторство після події?"), (sofia, olena, "Доброго дня! Порадите, з чого краще почати FastAPI-проєкт?")]
    for sender, receiver, body in pairs:
        if sender and receiver and not db.query(DirectMessage).filter(DirectMessage.sender_id == sender.id, DirectMessage.receiver_id == receiver.id, DirectMessage.body == body).first():
            db.add(DirectMessage(sender_id=sender.id, receiver_id=receiver.id, body=body))
            inserted["messages"] += 1
    db.commit()

    try:
        if (db.execute(text("SELECT COUNT(*) FROM iot_visits")).scalar() or 0) == 0:
            rows = []
            for event in db.query(Event).order_by(Event.start_time.asc()).limit(3).all():
                rows.extend([
                    {"event_id": event.id, "device_id": "door-main", "direction": "in", "delta": 1},
                    {"event_id": event.id, "device_id": "door-main", "direction": "in", "delta": 1},
                    {"event_id": event.id, "device_id": "door-side", "direction": "out", "delta": -1},
                ])
            for row in rows:
                db.execute(text("INSERT INTO iot_visits (event_id, device_id, direction, delta) VALUES (:event_id, :device_id, :direction, :delta)"), row)
            db.commit()
            inserted["iot"] = len(rows)
    except Exception:
        db.rollback()

    return inserted
