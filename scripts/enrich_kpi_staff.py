"""Apply manually verified diploma facts from the linked official staff profiles."""
import json
from pathlib import Path

SPECIALTIES = {
    'koval': 'Прикладна математика',
    'barabash': 'Авіаційне електро- та приладне обладнання',
    'varava': 'Інформаційні технології проектування',
    'verlan': 'Електронні обчислювальні машини',
    'haharin': 'Електронні обчислювальні машини',
    'husieva': 'Програмне забезпечення автоматизованих систем',
    'datsiuk': 'Системи автоматизованого проектування',
    'dmytrenko': 'Прикладна математика',
    'kolumbet': 'Програмне забезпечення автоматизованих систем',
    'kuzminykh': 'Автоматизовані системи управління',
    'musiienko': 'Математика; Телекомунікаційні системи та мережі',
    'nedashkivskyi': "Інформаційні мережі зв’язку; Управління суспільним розвитком",
}


def main():
    path = Path(__file__).resolve().parents[1] / 'app/data/kpi_staff.json'
    records = json.loads(path.read_text(encoding='utf-8'))
    for record in records:
        record.setdefault('source_full_name', record['full_name'])
        parts = record['source_full_name'].split()
        record['full_name'] = parts[0] + ' ' + parts[-1]
        from app.services.profile_catalog import transliterate
        record['full_name_en'] = transliterate(record['full_name'])
        record['diploma_specialty'] = SPECIALTIES.get(record['slug'])
        if record['slug'] == 'dmytrenko':
            record['contact_emails'] = ['o_dmytrenko@lll.kpi.ua']
            record['contact_source'] = 'https://pma.fpm.kpi.ua/uk/teachers/dmitrenko-oleksandra-anatoliyivna'
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Updated verified specialty and contact facts; unknown diploma specialties remain empty.')


if __name__ == '__main__':
    main()
