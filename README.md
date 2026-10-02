# AlumnixHub

Веб-система адміністрування Telegram-бота для комунікації випускників університету.  
Web-based Telegram bot administration and university alumni communication platform.

**Website / Сайт:** http://77.47.192.6:4063/  
**Telegram:** https://t.me/NniteUnity_bot

## Українська

### Реєстрація та профіль
1. Зареєструйтеся, вказавши власну електронну адресу.
2. Перейдіть за посиланням підтвердження з листа. Перевірте спам; без підтвердження вхід недоступний.
3. Заповніть профіль: ім'я українською та англійською, факультет, спеціальність, групу, рік випуску, опис, навички, інтереси та місце проживання.
4. За бажанням увімкніть менторство й зазначте напрям допомоги. Це не надає адміністративних прав.

### Використання сайту
| Розділ | Можливості |
| --- | --- |
| Головна | Актуальні матеріали й можливості спільноти |
| Події | Пошук, календар, повний опис, реєстрація й QR-посилання для реєстрації |
| Мої події | Власні реєстрації; доступність залежить від строків та вільних місць |
| Новини | Опубліковані матеріали спільноти та КПІ |
| Випускники | Пошук людей за інформацією профілю |
| Ментори | Пошук за навичками та напрямом допомоги |
| Повідомлення | Особисте спілкування зареєстрованих користувачів |
| Чати | Групове спілкування |
| Опитування | Надсилання відповідей після входу, доступні результати й діаграми |
| Сповіщення | Повідомлення про активність |

Рекомендації враховують інтереси та активність. Перемикач UA/EN змінює інтерфейс. Переклади матеріалів через DeepL кешуються; при недоступності сервісу може залишатися оригінальний текст. Закриті демонстраційні анкети із синтетичними відповідями не є реальними результатами дослідження.

### Telegram
У профілі відкрийте підключення Telegram, оберіть згоду на потрібні сповіщення, перейдіть за персональним посиланням і натисніть Start. Не передавайте це посилання іншій людині.

Бот відкриває події, новини, профіль, повідомлення, опитування й файли. /menu відкриває меню; /stop припиняє підписку. Посилання на сайт потребують окремого входу в браузері. Адміністративний вхід і особистий профіль мають різні права.

### Адміністрування
Адміністратор входить з приватно наданими обліковими даними та керує подіями, новинами, користувачами, анкетами, файлами й аналітикою. Щоденний імпорт КПІ додає матеріали на перевірку, а не публікує їх автоматично. Перевірте текст, переклад, зображення та згенерований короткий опис перед публікацією.

У розділі ботів перевіряйте підключення, обирайте аудиторію лише серед користувачів зі згодою та переглядайте статуси доставки. Прийняття повідомлення Telegram не означає його прочитання.

### Сервер і база даних
Сайт працює на університетському сервері незалежно від ноутбука. Зовнішній порт — **4063**. Для PuTTY: сервер 77.47.192.6, SSH-порт **22**, користувач std19.

Контейнер alumnixhub-std19 запускає сайт і обробник Telegram; його внутрішній порт 8000 відображається на 4063. Закриття PuTTY не зупиняє сервіс. Не запускайте другий локальний обробник того самого бота.

SQLite зберігається на сервері в /home/std19/alumnixhub/data/dev.db, підключеному до контейнера як /data/dev.db. Перезапуск і оновлення контейнера зберігають базу та окремий каталог uploads. Локальна й серверна бази не синхронізуються автоматично.

Ліміту кількості профілів у застосунку немає. База росте разом із записами, повідомленнями та аналітикою, але диск автоматично не розширюється. SQLite допускає один запис одночасно: кількість збережених користувачів не визначає допустиму кількість одночасних відвідувачів. Для значного навантаження на записи потрібен PostgreSQL.

Поточне підключення HTTP не шифрує трафік. Для захищеної публічної експлуатації потрібні домен і HTTPS.

[Обслуговування та резервні копії](DEPLOYMENT.md) · [JMeter і результати тесту](tests/performance/README.md)

## English

### Registration and Profile
1. Register using an email address you control.
2. Follow the emailed verification link. Check spam; login requires verification.
3. Complete your Ukrainian and English names, faculty, specialty, cohort, graduation year, biography, skills, interests and location.
4. Optionally enable mentoring and describe how you can help. Mentoring does not grant administrative access.

### Using the Website
| Area | Available actions |
| --- | --- |
| Home | Browse current community content and opportunities |
| Events | Search, use the calendar, read full details, register and generate a registration QR link |
| My events | Review registrations; availability depends on deadlines and capacity |
| News | Read published community and KPI articles |
| Alumni | Find people using profile filters |
| Mentors | Find mentors by skills and support areas |
| Messages | Contact other registered users through personal accounts |
| Chats | Participate in group conversations |
| Surveys | Submit answers after login and view available results and charts |
| Notifications | Review activity notifications |

Recommendations use interests and website activity. UA/EN changes the interface language. DeepL content translations are cached; original text can remain visible when translation is unavailable. Closed demonstration surveys with synthetic answers are not real research findings.

### Telegram
Open Telegram linking in your profile, select notification consent, follow your personal link and press Start. Do not share your linking link.

The bot provides events, news, profiles, messages, surveys and files. /menu opens the menu; /stop unsubscribes. Website links require a separate browser login. Administrator sessions and personal accounts have different permissions.

### Administration
Use the administrator login with privately supplied credentials. Administrators manage events, news, accounts, surveys, files and analytics. Daily KPI imports enter a review queue rather than publishing automatically. Review text, translations, images and generated short descriptions before publication.

In bot administration, check connection status, select only consenting recipients and inspect delivery results. Acceptance by Telegram does not prove that a message was read.

### Server and Database
The website runs on the university server independently of a laptop. Public port: **4063**. PuTTY uses host 77.47.192.6, SSH port **22**, username std19.

The alumnixhub-std19 container runs the website and Telegram worker. Internal port 8000 maps to public port 4063. Closing PuTTY leaves it running. Do not run a competing local worker for the same bot.

SQLite lives at /home/std19/alumnixhub/data/dev.db, mounted as /data/dev.db. Container restarts and source updates preserve the database and the separate uploads directory. Laptop and server databases do not synchronize automatically.

There is no fixed account limit in the application. The file grows with records, messages and analytics, but storage does not expand automatically. SQLite permits one writer at a time: stored account capacity is not concurrent visitor capacity. Use PostgreSQL for substantial write-heavy workloads.

The current HTTP endpoint does not encrypt traffic. A domain and HTTPS are needed for secure public production use.

[Maintenance and backups](DEPLOYMENT.md) · [JMeter test and results](tests/performance/README.md)
