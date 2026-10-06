# Profile Catalogs / Довідники профілю

## Українська

- Країна обирається зі списку; місто вводиться окремо. Сервер перевіряє код країни.
- `app/data/countries.json`: 249 країн і територій ISO 3166, alpha-2, alpha-3,
  числовий код, українська й англійська назви, латинська транслітерація для пошуку.
  Джерела: pycountry/iso-codes та Unicode CLDR через Babel.
- Спеціальності мають окремі записи за класифікаціями: історична, 2015, від 2025.
  Рік випуску лише підказує класифікацію. Обирайте код, зазначений у дипломі.
  Старі й нові спеціальності не об'єднуються автоматично: відповідність не завжди однозначна.
- Адміністратор: Адміністрування → Спеціальності
  (`/admin/operations/specialties`). Вкажіть класифікацію, код та обидві назви.
  Зняття позначки доступності приховує запис від нового вибору, а не видаляє його.
- Професійний статус описує зайнятість або готовність до співпраці, а не роль
  чи права доступу. Приклади: «Шукаю роботу», «Відкрита до співпраці».
  Поточна посада й компанія залишаються окремими полями.
- Нові таблиці створюються під час запуску; наявні профілі не видаляються.
  Повторний запуск не перезаписує адміністративні зміни довідника.
- Рік випуску: від 1965 до поточного року, не раніше вступу та щонайменше
  через 15 років після року народження. Без дати народження нижня межа — 1965.
  Дата народження не може бути майбутньою. Рік вступу є необов'язковим.

## English

- Select a country; enter the city separately. The server validates the country code.
- The country JSON contains 249 ISO 3166 countries and territories, alpha-2,
  alpha-3, numeric identifiers, Ukrainian/English names and Latin search transliterations.
  Data sources: pycountry/iso-codes and Unicode CLDR through Babel.
- Specialty records are separated into historical, 2015 and from-2025 classifications.
  Graduation year is a suggestion, not a restriction: select the actual diploma code.
  Historical and current specialties are not automatically treated as equivalent.
- Administrators use `/admin/operations/specialties` to add or edit codes and both
  language labels. Disable selection instead of deleting referenced records.
- Professional status is employment/collaboration information, not an account role
  or permission. Job title and employer remain separate fields.
- Startup creates new tables without deleting profiles and preserves administrator edits.
- Graduation year is between 1965 and the current year, no earlier than admission,
  and at least 15 years after birth year when supplied. Birth date cannot be in the future.
  Admission year is optional. The English view uses Latin transliteration for Ukrainian city names.

## Specialty Sources

- https://kpi.ua/score-13
- https://kpi.ua/2025-score
- https://osvita.kpi.ua/sites/default/files/downloads/Tabliza_vidpovidnosti_0.pdf
- https://kpi.ua/files/licence-2018.pdf

Country catalog regeneration is a maintainer task using `scripts/build_country_catalog.py`;
pycountry and Babel are build-time dependencies, not required to select countries at runtime.

## Verification

```text
python -m pytest -ra
node tests/profile_catalog_frontend.test.cjs
```

The JavaScript checks exercise classification suggestions, manual overrides and dynamic date
limits with a simulated form. They are not a substitute for visual browser testing.
