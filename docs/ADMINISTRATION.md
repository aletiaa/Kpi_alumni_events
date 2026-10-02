# Administration / Адміністрування

## Українська

### Права доступу
Відкрийте **Адміністрування → Адміністратори**. Початковий адміністратор або
керівник адміністраторів може призначити активного користувача з підтвердженим
email адміністратором або керівником, а також відкликати його доступ.
Потрібні власний пароль і підтвердження дії. Звичайний адміністратор не може
призначати інших адміністраторів. Змінювати власні права через цю форму не можна.
Початковий адміністративний обліковий запис залишається для відновлення доступу.
Новому адміністратору слід повторно ввійти для оновлення меню; захищені дії
перевіряють права в базі при кожному запиті, навіть зі старим сеансом.

### Telegram і модерація
Кожен активний адміністратор із підтвердженим email може підключити власний
Telegram у розділі ботів. Персональне посилання діє 10 хвилин і використовується
один раз. Не передавайте його іншій людині. Це не замінює авторизацію на сайті.

Підключений користувач може натиснути **Submit news** або надіслати:

```text
/submit_news Заголовок
Текст матеріалу
```

Матеріал стає чернеткою, а не публічною новиною. У розділі **Матеріали з Telegram**
адміністратор редагує, підтверджує перевірку та публікує або відхиляє матеріал.
Обмеження: три пропозиції на годину, заголовок до 200 символів, текст до 10000.
Ця команда приймає текст; завантаження файлів є окремою функцією.

### Інтереси та журнал
У **Каталозі інтересів** можна додавати тематики, назви двома мовами та синоніми,
а також вимикати тематики. У профілі користувач обирає інтереси прапорцями.
Рекомендації пояснюють тематичний збіг і не враховують частоту повторення слів.
Вбудовані тематики мають базові правила розпізнавання, додаткові синоніми
задаються через сайт. Для повного виключення тематики вимкніть її.
**Журнал дій** фіксує адміністративні POST-запити, виконавця та HTTP-результат;
паролі, тіла запитів і персональні коди підключення не записуються.

### Резервні копії
При `BACKUP_ENABLED=true` сервер щогодини перевіряє, чи потрібна нова копія:
інтервал між копіями не менший ніж 24 години. Зберігаються останні 14 архівів.
Копія містить узгоджений знімок SQLite, завантаження та приватні налаштування.
Перед додаванням до реєстру перевіряються SHA-256 і цілісність тимчасово
відновленої бази. Робоча база під час перевірки не замінюється.
Керівник може створити копію вручну та повторити перевірку через сайт.
Завантаження приватних архівів через браузер не передбачено.
Архіви розташовані в `/home/std19/alumnixhub/data/backups` і не потрапляють у Git.
Вони зберігаються на тому самому сервері: для захисту від втрати всього сервера
потрібна додатково погоджена зовнішня копія. Відновлення робочої бази виконує
оператор сервера після зупинки застосунку, з попередньою копією поточної бази.

### HTTPS
Поточна адреса залишається HTTP на порту 4063. Для довіреного HTTPS потрібне
погодження адміністратора університетського сервера: домен/піддомен із TLS-проксі
до застосунку або дозволена перевірка IP-сертифіката. Не займайте спільні порти
80/443 самостійно. Самого порту 4063 недостатньо для HTTP-01 перевірки.
До налаштування HTTPS не використовуйте платформу для чутливих реальних даних.

## English

### Access
Open **Administration → Administrators**. The initial administrator or an
administrator manager can grant administrator/manager access to an active,
email-verified user, or revoke it. Your password and explicit confirmation are
required. Ordinary administrators cannot appoint administrators. You cannot
change your own privileges through this form. The bootstrap administrator stays
available for recovery. Sign in again after appointment to refresh navigation;
protected requests recheck database privileges even for existing sessions.

### Telegram submissions
Active email-verified administrators can link their own Telegram account through
a personal, single-use, ten-minute link in the bot dashboard. Never share it.
Website sign-in is still required for website administration.
Linked users can select **Submit news** or send `/submit_news Title` followed by
a newline and the article body. It creates a draft. Administrators review/edit
it under **Telegram submissions**, then confirm publication or rejection.
Limits: three submissions per hour, 200-character title, 10000-character body.
This command accepts text; file submission is separate.

### Topics and auditing
Manage bilingual labels, additional aliases and active status under **Interest
catalog**. Users select interests in their profile. Recommendations explain topic
matches, not repeated-word frequency. Built-in topics retain their base matching
rules; disable a topic to exclude it completely.
**Audit log** records administrative POST paths, actors and HTTP results, not
passwords, request bodies or personal linking codes.

### Backups
With `BACKUP_ENABLED=true`, the worker checks hourly and creates a backup when
the latest is at least 24 hours old. The latest 14 archives are retained.
Archives contain a consistent SQLite snapshot, uploads and private settings.
SHA-256 and a temporary restored database's integrity are verified before
registration. Verification never replaces the live database. Managers can
create and verify server-side copies through the website, but cannot download
private archives through the browser. Archives live under
`/home/std19/alumnixhub/data/backups`, outside Git. Same-server backups do not
protect against loss of the entire server; off-server copies require separate
arrangements. A server operator restores the live database with the application
stopped and a fresh copy of its previous database preserved.

### HTTPS
The current service remains HTTP on port 4063. Trusted HTTPS requires the
university server administrator to provide a domain/TLS reverse proxy or approve
IP certificate validation routing. Do not occupy shared ports 80/443 yourself.
Port 4063 alone cannot satisfy HTTP-01 validation. Avoid sensitive real-world
data until HTTPS is configured.
