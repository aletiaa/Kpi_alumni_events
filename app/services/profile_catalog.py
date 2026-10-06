import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from markupsafe import Markup
from app.models import ProfileReference, SpecialtyDefinition


@lru_cache(maxsize=1)
def countries():
    return json.loads((Path(__file__).resolve().parents[1] / "data/countries.json").read_text(encoding="utf-8"))


def country_by_code(code):
    return next((c for c in countries() if c["alpha2"] == code), None)


def legacy_location(value):
    parts = (value or "").split(",", 1)
    label = parts[0].strip().casefold()
    match = next((c for c in countries() if label in
        {c[k].casefold() for k in ("alpha2", "alpha3", "name_uk", "name_en", "transliteration")}), None)
    return (match["alpha2"], parts[1].strip() if len(parts)>1 else "") if match else (None, "")


def profile_reference(db, user):
    row = db.get(ProfileReference, user.id)
    if row:
        return row
    code, city = legacy_location(user.city_country)
    return ProfileReference(user_id=user.id, country_code=code, city=city)


def bilingual(uk, en):
    return Markup('<span data-no-translate data-ops-uk="{}" data-ops-en="{}">{}</span>').format(uk, en, uk)


def display_location(user):
    code, city = legacy_location(user.city_country)
    country = country_by_code(code)
    if not country:
        return ""
    suffix = ", " + city if city else ""
    en_suffix = ', ' + transliterate(city) if city else ''
    return bilingual(country["name_uk"] + suffix, country["name_en"] + en_suffix)


def transliterate(text):
    pairs = dict(zip("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя",
        ["a","b","v","h","g","d","e","ie","zh","z","y","i","i","i","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","iu","ia"]))
    initial = {"є":"ye", "ї":"yi", "й":"y", "ю":"yu", "я":"ya"}
    result, start = [], True
    for char in text:
        if char in "'’ьЬ":
            continue
        lower = char.lower()
        value = initial.get(lower, pairs.get(lower, char)) if start else pairs.get(lower, char)
        result.append(value.capitalize() if char.isupper() else value)
        start = not char.isalpha()
    return ''.join(result).replace('zhh', 'zgh')


def role_label(role):
    labels = {'alumni': ('Випускник', 'Alumnus'), 'student': ('Студент', 'Student'),
              'guest': ('Учасник спільноти', 'Community participant'),
              'admin': ('Адміністратор', 'Administrator'), 'mentor': ('Ментор', 'Mentor')}
    return bilingual(*labels.get(role, ('Учасник', 'Participant')))


def professional_status(user):
    value = (user.status or '').strip()
    return value if value.casefold() not in {'alumni', 'admin', 'student', 'guest'} else ''


def graduation_display(user):
    year = user.graduation_year
    if not year or not 1965 <= year <= date.today().year:
        return ''
    if user.birth_date and (user.birth_date > date.today() or year < user.birth_date.year + 15):
        return ''
    return year


def seed_specialties(db):
    from app.services.specialties import KPI_SPECIALTIES
    rows = json.loads((Path(__file__).resolve().parents[1] / "data/specialties.json").read_text(encoding="utf-8"))
    english_names = [
        'Economics', 'Psychology', 'Sociology', 'Journalism', 'Management', 'Marketing', 'Law',
        'Ecology', 'Physics and astronomy', 'Applied physics and nanomaterials', 'Applied mathematics',
        'Software engineering', 'Computer science', 'Computer engineering', 'Systems analysis',
        'Cybersecurity and information protection', 'Information systems and technologies',
        'Applied mechanics', 'Materials science', 'Industrial mechanical engineering',
        'Aviation and aerospace engineering', 'Electrical power engineering and electromechanics',
        'Power machinery engineering', 'Nuclear power engineering', 'Thermal power engineering',
        'Automation and computer-integrated technologies', 'Metrology and information-measuring equipment',
        'Micro- and nanosystem engineering', 'Chemical technologies and engineering',
        'Biotechnology and bioengineering', 'Biomedical engineering', 'Electronics',
        'Electronic communications and radio engineering', 'Avionics',
        'Automation, computer-integrated technologies and robotics', 'Information-measuring technologies',
        'Micro- and nanosystem engineering', 'Mining', 'Publishing and printing',
        'Therapy and rehabilitation', 'Public administration']
    rows += [dict(code=r["code"], name_uk=r["name"], name_en=en, classification="2015",
                  source_url="https://kpi.ua/2025-score") for r,en in zip(KPI_SPECIALTIES, english_names, strict=True)]
    historical = [
        ('6.050103', 'Програмна інженерія', 'Software engineering'),
        ('6.050102', "Комп'ютерна інженерія", 'Computer engineering'),
        ('6.050201', 'Системна інженерія', 'Systems engineering'),
        ('6.050202', "Автоматизація та комп'ютерно-інтегровані технології", 'Automation and computer-integrated technologies'),
        ('6.050801', 'Мікро- та наноелектроніка', 'Micro- and nanoelectronics'),
        ('6.050901', 'Радіотехніка', 'Radio engineering'),
        ('6.050903', 'Телекомунікації', 'Telecommunications'),
        ('6.050701', 'Електротехніка та електротехнології', 'Electrical engineering and technologies'),
        ('6.050702', 'Електромеханіка', 'Electromechanics'),
        ('6.050601', 'Теплоенергетика', 'Thermal power engineering'),
        ('6.050603', 'Атомна енергетика', 'Nuclear power engineering'),
        ('6.050501', 'Прикладна механіка', 'Applied mechanics'),
        ('6.050502', 'Інженерна механіка', 'Engineering mechanics'),
        ('6.050503', 'Машинобудування', 'Mechanical engineering'),
        ('6.051301', 'Хімічна технологія', 'Chemical technology'),
        ('6.051401', 'Біотехнологія', 'Biotechnology'),
        ('6.051402', 'Біомедична інженерія', 'Biomedical engineering'),
        ('6.030601', 'Менеджмент', 'Management'),
        ('6.040106', 'Екологія', 'Ecology'),
        ('6.050301', 'Гірництво', 'Mining'),
        ('6.030504', 'Економіка підприємства', 'Enterprise economics'),
        ('6.030502', 'Економічна кібернетика', 'Economic cybernetics'),
        ('6.030503', 'Міжнародна економіка', 'International economics'),
        ('6.030507', 'Маркетинг', 'Marketing'),
        ('6.030101', 'Соціологія', 'Sociology'),
        ('6.030402', 'Правознавство', 'Law'),
        ('6.020303', 'Філологія', 'Philology'),
        ('6.040201', 'Математика', 'Mathematics'),
        ('6.040203', 'Фізика', 'Physics'),
        ('6.040204', 'Прикладна фізика', 'Applied physics'),
        ('6.050401', 'Металургія', 'Metallurgy'),
        ('6.050402', 'Ливарне виробництво', 'Foundry production'),
        ('6.050403', 'Інженерне матеріалознавство', 'Engineering materials science'),
        ('6.050604', 'Енергомашинобудування', 'Power machinery engineering'),
        ('6.050902', 'Радіоелектронні апарати', 'Radioelectronic equipment'),
        ('6.051003', 'Приладобудування', 'Instrument engineering'),
        ('6.010203', "Здоров'я людини", 'Human health'),
        ('6.050504', 'Зварювання', 'Welding'),
        ('6.051001', 'Метрологія та інформаційно-вимірювальні технології', 'Metrology and measurement technologies'),
        ('6.051101', 'Авіа- та ракетобудування', 'Aircraft and rocket engineering'),
        ('6.051103', 'Авіоніка', 'Avionics'),
        ('6.050802', 'Електронні пристрої та системи', 'Electronic devices and systems'),
        ('6.050803', 'Акустотехніка', 'Acoustic engineering'),
        ('6.020205', 'Образотворче мистецтво', 'Fine arts'),
        ('6.030303', 'Видавнича справа та редагування', 'Publishing and editing'),
        ('6.030302', "Реклама і зв'язки з громадськістю", 'Advertising and public relations'),
        ('6.051501', 'Видавничо-поліграфічна справа', 'Publishing and printing'),
        ('6.051004', 'Оптотехніка', 'Optical engineering'),
        ('6.170101', 'Безпека інформаційних і комунікаційних систем', 'Information and communication systems security'),
        ('6.170102', 'Системи технічного захисту інформації', 'Technical information protection systems'),
    ]
    rows += [dict(code=c, name_uk=uk, name_en=en, classification='legacy',
                  source_url='https://kpi.ua/score-13') for c,uk,en in historical]
    modern = [
        ('B2', 'Дизайн', 'Design'), ('B4', 'Образотворче мистецтво та реставрація', 'Fine arts and restoration'),
        ('B11', 'Філологія', 'Philology'), ('C7', 'Журналістика', 'Journalism'),
        ('C1.01', 'Економіка', 'Economics'), ('C1.02', 'Міжнародні економічні відносини', 'International economic relations'),
        ('C3', 'Міжнародні відносини', 'International relations'), ('C4', 'Психологія', 'Psychology'),
        ('C5', 'Соціологія', 'Sociology'), ('D2', 'Фінанси, банківська справа, страхування та фондовий ринок', 'Finance, banking, insurance and stock market'),
        ('D3', 'Менеджмент', 'Management'), ('D4', 'Публічне управління та адміністрування', 'Public administration'),
        ('D5', 'Маркетинг', 'Marketing'), ('D7', 'Торгівля', 'Trade'), ('D8', 'Право', 'Law'),
        ('I7', 'Терапія та реабілітація', 'Therapy and rehabilitation'), ('I10', 'Соціальна робота та консультування', 'Social work and counselling'),
        ('G4.03', 'Відновлювані джерела енергії та гідроенергетика', 'Renewable energy and hydropower'),
    ]
    rows += [dict(code=c, name_uk=uk, name_en=en, classification='2025',
                  source_url='https://kpi.ua/2025-score') for c,uk,en in modern]
    for data in rows:
        key = data["classification"] + ":" + data["code"]
        if not db.get(SpecialtyDefinition, key):
            db.add(SpecialtyDefinition(key=key, **data))
    db.commit()
