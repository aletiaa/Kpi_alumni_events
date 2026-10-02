import re
from app.models import InterestTopic
from app.services.interest_topics import TOPICS, PATTERNS, topics

LABELS = {
    "python": ("Python", "Python"), "data": ("Аналітика даних", "Data analytics"),
    "ai": ("Штучний інтелект", "Artificial intelligence"),
    "cybersecurity": ("Кібербезпека", "Cybersecurity"),
    "robotics": ("Робототехніка", "Robotics"), "mentoring": ("Менторство", "Mentoring"),
    "career": ("Кар'єра", "Career"), "startup": ("Стартапи", "Startups"),
    "product": ("Управління продуктом", "Product management"),
    "frontend": ("Фронтенд", "Frontend"), "backend": ("Бекенд", "Backend"),
    "javascript": ("JavaScript", "JavaScript"), "cloud": ("Хмарні технології", "Cloud"),
    "databases": ("Бази даних", "Databases"), "design": ("Дизайн", "Design"),
    "testing": ("Тестування", "Software testing"), "networking": ("Нетворкінг", "Networking"),
    "research": ("Дослідження", "Research"), "electronics": ("Електроніка", "Electronics"),
    "finance": ("Фінанси", "Finance"), "marketing": ("Маркетинг", "Marketing"),
    "management": ("Управління проєктами", "Project management"),
    "languages": ("Іноземні мови", "Languages"), "literature": ("Література", "Literature"),
}


def seed_catalog(db):
    for key in TOPICS:
        if not db.get(InterestTopic, key):
            uk, en = LABELS[key]
            db.add(InterestTopic(key=key, label_uk=uk, label_en=en))
    db.commit()


def catalog_topics(text, catalog):
    if not catalog:
        return topics(text)
    found = set()
    for item in catalog:
        if not item.is_active:
            continue
        if item.key in PATTERNS and PATTERNS[item.key].search(text or ""):
            found.add(item.key)
            continue
        aliases = [item.label_uk, item.label_en, item.key] + item.aliases.splitlines()
        if any(re.search(r"(?<!\w)" + re.escape(alias.strip()) + r"(?!\w)", text or "", re.I)
               for alias in aliases if alias.strip()):
            found.add(item.key)
    return found
