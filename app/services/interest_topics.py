"""Bilingual topic recognition; repeated words do not increase relevance."""
import re

TOPICS = {
    "python": r"python|пайтон\w*|пітон\w*",
    "data": r"data science|data analytics|data analysis|data engineering|аналітик\w*|аналіз даних|наук\w* про дані|інженер\w* даних",
    "ai": r"ai|ml|artificial intelligence|machine learning|штучн\w* інтелект\w*|машинн\w* навчан\w*",
    "cybersecurity": r"cybersecurity|cyber security|кібербезпек\w*|кіберзахист\w*|інформаційн\w* безпек\w*",
    "robotics": r"robotics|robots?|sensors?|робототехнік\w*|робот\w*|сенсор\w*",
    "mentoring": r"mentoring|mentorship|ментор\w*|наставництв\w*",
    "career": r"career|careers|cv|resume|кар['’]єр\w*|резюме|працевлаштуван\w*",
    "startup": r"startups?|entrepreneurship|стартап\w*|підприємництв\w*",
    "product": r"product management|product discovery|продукт\w* менеджмент\w*|управління продукт\w*",
    "frontend": r"frontend|front end|react|vue|angular|фронтенд\w*",
    "backend": r"backend|back end|fastapi|django|бекенд\w*",
    "javascript": r"javascript|typescript|js|ts",
    "cloud": r"cloud|aws|azure|devops|kubernetes|docker|хмар\w*|девопс\w*",
    "databases": r"databases?|sql|postgresql|sqlite|баз\w* даних",
    "design": r"ux|ui|design|дизайн\w*",
    "testing": r"qa|software testing|тестуван\w*",
    "networking": r"networking|alumni meetup|нетворкінг\w*|зустріч\w* випускник\w*",
    "research": r"research|science|досліджен\w*|науков\w*",
    "electronics": r"electronics|radio|електронік\w*|радіотехнік\w*",
    "finance": r"finance|financial|фінанс\w*",
    "marketing": r"marketing|маркетинг\w*",
    "management": r"project management|управління проєкт\w*|управління проект\w*",
    "languages": r"english|languages|англійськ\w*|іноземн\w* мов\w*",
    "literature": r"literature|poetry|літератур\w*|поезі\w*",
}
PATTERNS = {topic: re.compile(r"(?<!\w)(?:" + aliases + r")(?!\w)", re.I)
            for topic, aliases in TOPICS.items()}


def topics(text):
    return {topic for topic, pattern in PATTERNS.items() if pattern.search(text or "")}
