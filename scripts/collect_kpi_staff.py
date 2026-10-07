"""Collect the requested public staff records. Requires beautifulsoup4==4.13.4."""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from app.services.profile_catalog import transliterate

SOURCE = 'https://iate.kpi.ua/about/departments/software-engineering-in-energy/academic-staff/'
AREAS = {
    'Коваль': ('Інформаційний пошук; дані та знання; моделювання ПЗ', 'Information retrieval; data and knowledge; software modelling'),
    'Бандурка': ('Економіка ІТ; підприємництво; геоаналітика', 'IT economics; entrepreneurship; geospatial analytics'),
    'Барабаш': ('Алгоритми; структури даних; інформаційні системи', 'Algorithms; data structures; information systems'),
    'Варава': ('Якість ПЗ; тестування', 'Software quality; testing'),
    'Верлань': ('Аналіз даних; енергетика; сталий розвиток', 'Data analysis; energy; sustainable development'),
    'Гаврилко': ('Кібербезпека; приватність; децентралізовані застосунки', 'Cybersecurity; privacy; decentralised applications'),
    'Гагарін': ('Системне програмування; веброзробка; мультимедіа', 'Systems programming; web development; multimedia'),
    'Гусєва': ('Програмування; мережі; захист програмних засобів', 'Programming; networks; software protection'),
    'Дацюк': ('Бази даних; бази знань; алгоритми', 'Databases; knowledge bases; algorithms'),
    'Дмитренко': ('Розробка ПЗ; кіберфізичні системи', 'Software development; cyber-physical systems'),
    'Залевська': ('Методологія інженерії програмного забезпечення', 'Software engineering methodology'),
    'Колумбет': ('Програмна інженерія; складні алгоритми', 'Software engineering; advanced algorithms'),
    'Кузьміних': ('Моделювання; автоматизоване проєктування', 'Modelling; computer-aided design'),
    'Мусієнко': ('Діагностичні системи; інтелектуальне ПЗ', 'Diagnostic systems; intelligent software'),
    'Недашківський': ('Мобільні застосунки; кросплатформна розробка; веб', 'Mobile applications; cross-platform development; web'),
}


def fetch(url):
    url = quote(url, safe=':/%?=&+#')
    with urlopen(Request(url, headers={'User-Agent': 'AlumnixHubStaffImport/1.0'}), timeout=30) as response:
        data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise ValueError('Page too large')
        return BeautifulSoup(data, 'html.parser')


def collect():
    roster = fetch(SOURCE)
    cards = roster.select('article.iate-staff-card')
    first_profile = cards[0].select_one('a.iate-document-link')['href']
    first = fetch(first_profile)
    contact_link = next(a['href'] for a in first.select('a[href]') if a.get_text(' ', strip=True) == 'Контакти викладачів кафедри')
    contacts = fetch(urljoin(first_profile, contact_link))
    contact_rows = contacts.select('table tr')
    records, research = [], []
    for surname, (uk, en) in AREAS.items():
        card = next(c for c in cards if surname in c.select_one('h2').get_text())
        full_name = card.select_one('h2').get_text(' ', strip=True)
        profile = card.select_one('a.iate-document-link')['href']
        page = first if profile == first_profile else fetch(profile)
        image = card.select_one('img')
        if image is None:
            image = page.select_one('article img')
        photo = urljoin(profile, image.get('src', '')) if image else None
        contact = next((r for r in contact_rows if surname.casefold() in r.get_text().casefold().replace('i', 'і')), None)
        cells = contact.find_all(['td', 'th']) if contact else []
        detail = cells[-1].get_text(' ', strip=True) if cells else ''
        emails = list(dict.fromkeys(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', detail)))
        telegram = re.search(r'(?<!\w)@([A-Za-z][A-Za-z0-9_]{4,31})(?!\w)', detail)
        slug = transliterate(surname).lower()
        role = card.select_one('.iate-staff-role').get_text(' ', strip=True)
        paragraphs = [p.get_text(' ', strip=True) for p in page.select('article p')]
        research.append({'surname': surname, 'profile_url': profile, 'photo_url': photo,
            'education': [p for p in paragraphs if any(w in p.casefold() for w in ['закінч', 'спеціальн', 'email', 'e-mail'])]})
        records.append({'slug': slug, 'full_name': full_name, 'full_name_en': transliterate(full_name),
            'position': role, 'areas_uk': uk, 'areas_en': en, 'photo_url': photo,
            'profile_url': profile, 'source_url': SOURCE, 'contact_source': urljoin(first_profile, contact_link),
            'contact_emails': emails, 'contact_telegram': telegram.group(1) if telegram else None,
            'login_email': slug + '@faculty.example.test', 'diploma_specialty': None,
            'checked_on': date.today().isoformat(), 'mentoring_confirmed': False})
    assert len(records) == 15 and len({r['login_email'] for r in records}) == 15
    root = Path(__file__).resolve().parents[1]
    (root / 'app/data/kpi_staff.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (root / '.pytest_cache/staff-research.json').write_text(json.dumps(research, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'profiles': len(records), 'photos': sum(bool(r['photo_url']) for r in records),
        'public_emails': sum(bool(r['contact_emails']) for r in records)}, ensure_ascii=False))


if __name__ == '__main__':
    collect()
