# AlumnixHub

Веб-система адміністрування Telegram-бота для комунікації випускників університету.  
Web-based Telegram bot administration and university alumni communication platform.

**Website / Сайт:** http://77.47.192.6:4063/  
**Telegram:** https://t.me/NniteUnity_bot

**Admin guide / Посібник адміністратора:** [docs/ADMINISTRATION.md](docs/ADMINISTRATION.md)

**Full Word guide / Повна інструкція Word:** [AlumnixHub_User_Guide_UA_EN.docx](docs/AlumnixHub_User_Guide_UA_EN.docx)

Ця інструкція пояснює щоденну роботу користувачів, адміністраторів і відповідального за сервер. Для використання сайту встановлювати програму на комп'ютер не потрібно.

This guide covers everyday tasks for users, administrators and the server operator. Website users do not need to install an application.

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

Рекомендації зіставляють тематики інтересів, а не частоту повторення слів. Адміністратор керує двомовним каталогом тематик та додатковими синонімами через сайт. Явно обрані інтереси мають пріоритет; за їх відсутності використовуються тематики реєстрацій та переглядів. Без тематичних сигналів рекомендацій немає. Це детермінований тематичний алгоритм, не генеративна модель. Перемикач UA/EN змінює інтерфейс. Переклади матеріалів через DeepL кешуються; при недоступності сервісу може залишатися оригінальний текст. Закриті демонстраційні анкети із синтетичними відповідями не є реальними результатами дослідження.

### Telegram
У профілі відкрийте підключення Telegram, оберіть згоду на потрібні сповіщення, перейдіть за персональним посиланням і натисніть Start. Не передавайте це посилання іншій людині.

Бот відкриває події, новини, профіль, повідомлення, опитування й файли. /menu відкриває меню; /stop припиняє підписку. Посилання на сайт потребують окремого входу в браузері. Адміністративний вхід і особистий профіль мають різні права.

### Покрокові сценарії користувача

**Вхід і відновлення доступу.** Відкрийте сайт, оберіть вхід і введіть email та пароль. Якщо пароль втрачено, скористайтеся відновленням пароля й посиланням із листа. Не передавайте пароль або посилання відновлення іншим людям. Якщо лист не надійшов, перевірте спам та зверніться до адміністратора; не створюйте дублікати акаунта.

**Редагування профілю.** У профілі заповніть біографію, навички, професійний статус, поточну посаду та організацію. Оберіть країну з довідника, а факультет або навчально-науковий інститут зазначте у відповідному полі. Виберіть спеціальність і код, що відповідають періоду навчання. Збережіть зміни та перевірте власну картку у каталозі. Налаштування публічності визначає видимість профілю для інших людей.

Роль «студент», «випускник» або «гість» описує зв'язок зі спільнотою. Професійний статус описує роботу або кар'єрний стан; це не стан блокування акаунта. Права адміністратора та ознака ментора є окремими налаштуваннями. Гість із акаунтом отримує персональні можливості, яких немає в анонімного відвідувача. Якщо коректний рік випуску студента менший за поточний рік, система переводить його у випускники; випуск у поточному році сам по собі ще не запускає таку зміну.

Дата народження не може бути в майбутньому. Рік випуску має бути від 1965 до поточного року, не раніше року вступу та щонайменше на 15 років пізніше року народження, якщо дата народження вказана. Рік вступу не може передувати року народження. Якщо дата народження не вказана, перевірка віку при випуску не застосовується, але інші обмеження залишаються.

**Реєстрація на подію.** Відкрийте «Події», знайдіть потрібну подію за назвою, тематикою або календарем, прочитайте повний опис і натисніть реєстрацію. Перевірте результат у «Моїх подіях». Якщо доступне скасування, скористайтеся ним на сторінці події. Обмеження кількості місць і строків можуть не дозволяти нову реєстрацію. QR-код унизу опису відкриває сторінку реєстрації, але не реєструє людину автоматично.

**Новини та рекомендації.** Оберіть власні інтереси у профілі, відкрийте новини або події та перегляньте запропоновані матеріали. Кнопки персональних рекомендацій використовують тематичні сигнали; слова «та», «що» й інші службові слова самі по собі не є інтересами. У проєкті також існує окремий алгоритм текстової подібності для пошуку подій. Рекомендації не є гарантією відповідності й не замінюють рішення користувача.

**Ментори та повідомлення.** Відкрийте каталог менторів, перегляньте спеціалізацію та опис допомоги. Для особистої розмови знайдіть іншого користувача в розділі повідомлень і надішліть повідомлення. Власний акаунт не показується як адресат. Доступність співрозмовника залежить від активності, підтвердження email, блокування та публічності профілю. Розділ чатів може відкривати посилання на зовнішні групи, а не окремий вбудований месенджер. Профілі викладачів із позначкою непідтвердженої участі не означають, що вони погодилися на менторство.

**Опитування.** Відкрийте доступне опитування, заповніть потрібні відповіді та надішліть форму. Перевірте повідомлення про результат. Доступ до результатів залежить від налаштувань анкети; закрита анкета не приймає нових відповідей.

### Що можна зробити через Telegram

1. Спочатку створіть і підтвердьте акаунт на сайті. Кнопка «Register / log in» у боті відкриває сайт, а не створює акаунт повністю всередині Telegram. Автоматичний імпорт аватара Telegram не слід очікувати.
2. Підключіть акаунт через персональне посилання з профілю. Звичайний `/start` без прив'язування не надає доступу до персональних даних.
3. Відкрийте `/menu`, оберіть новини або події й виконайте доступну дію. Частина кнопок відкриває сторінки сайту, де потрібен окремий вхід.
4. Для пропозиції новини надішліть `/submit_news Заголовок`, а з нового рядка додайте текст. Заголовок має містити не більше 200 символів, текст не більше 10000; дозволено до трьох пропозицій на годину. Новина потрапляє на модерацію і не публікується автоматично.
5. Для файлів використовуйте відповідну дію меню. Ліміт надсилання становить 20 МБ. Telegram-файли можуть зберігатися як посилання та ідентифікатори Telegram, а не як завантажені копії на сервері.
6. Змініть згоду на сповіщення у профілі або скористайтеся `/stop`, щоб припинити підписку.

Бот відповідає, коли працює серверний застосунок та його обробник Telegram. Натискання Start не запускає сервер. Якщо немає відповіді, відповідальний за сервер перевіряє контейнер і журнали; користувачу не потрібно запускати бот локально.

### Адміністрування
Адміністратор входить з приватно наданими обліковими даними та керує подіями, новинами, користувачами, анкетами, файлами й аналітикою. Щоденний імпорт КПІ додає матеріали на перевірку, а не публікує їх автоматично. Перевірте текст, переклад, зображення та згенерований короткий опис перед публікацією.

У розділі ботів перевіряйте підключення, обирайте аудиторію лише серед користувачів зі згодою та переглядайте статуси доставки. Прийняття повідомлення Telegram не означає його прочитання.

### Покрокові сценарії адміністратора

1. **Новини:** створіть матеріал або відкрийте пропозицію Telegram; перевірте заголовок, текст, переклад і зображення. Згенеруйте короткий опис, перевірте його та опублікуйте матеріал. Згенерований опис є автоматично відібраним текстом, а не гарантовано точним авторським переказом.
2. **Події:** заповніть назву, опис, дату, місце, тематику та обмеження реєстрації. Збережіть і перевірте сторінку події зі звичайного акаунта. Реєстрації на сайті та доступні дії бота використовують спільні дані.
3. **Користувачі:** знайдіть акаунт і перевірте роль, професійний статус, активність та підтвердження email. Змінюйте права лише уповноваженим людям. Перед блокуванням чи видаленням переконайтеся, що обрано правильний акаунт.
4. **Інші адміністратори:** призначайте права через інтерфейс керування користувачами, без зміни коду. Активний адміністратор із підтвердженим email може прив'язати власний Telegram персональним одноразовим посиланням. Прив'язування Telegram не створює адміністративну сесію браузера.
5. **Довідники:** додайте спеціальність із кодом, двомовною назвою та періодом застосування. Для однієї спеціальності можуть існувати різні коди: до 2015 року, у 2015–2024 роках та після 2024 року. Не замінюйте старі коди новими для всіх випускників. Країни обираються зі спільного довідника кодів і назв.
6. **Розсилки:** перевірте підключення бота, підготуйте текст, виберіть аудиторію зі згодою, перевірте кількість одержувачів і запустіть надсилання. Перегляньте помилки та результати доставки. Не повторюйте розсилку наосліп, якщо попередній результат невідомий.
7. **Опитування та файли:** перевіряйте питання й строки анкети до відкриття; переглядайте результати та модеровані файли через відповідні розділи.

### Перевірка сервера та типові проблеми

Відкрийте PuTTY, виберіть SSH, вкажіть сервер `77.47.192.6` і порт `22`. Увійдіть під виданим серверним акаунтом. Пароль сервера, токен бота та поштові ключі не повинні бути у цьому README чи GitHub.

Відповідальний за сервер може перевірити стан такими командами:

```sh
docker ps --filter name=alumnixhub-std19
docker logs --tail 100 alumnixhub-std19
curl -I http://127.0.0.1:4063/
```

Лише за потреби й після перевірки журналів перезапустіть сервіс:

```sh
docker restart alumnixhub-std19
```

Не видаляйте каталог даних, uploads або `.env` під час оновлення. Резервні копії перевіряйте за інструкцією обслуговування. Для налаштованого щоденного механізму узгоджено зберігання останніх 14 копій; сама наявність правила не замінює перевірку фактичного створення та відновлення архівів.

- **403:** перевірте, що потрібна дія доступна вашій ролі та що використовується належний адміністративний вхід.
- **Бот мовчить:** перевірте сервер, прив'язування акаунта і журнали. Не запускайте другого обробника того самого токена.
- **Лист не надходить:** перевірте спам, email і поштові налаштування. У діагностичних сценаріях відновлення можуть відображатися службові посилання; їх не слід публікувати чи передавати стороннім.
- **Не знаходить користувача:** перевірте ім'я, мову, публічність та стан акаунта; власний акаунт не є адресатом нової розмови.
- **Не зберігає дату:** перевірте хронологію народження, вступу та випуску.
- **Не реєструє на подію:** перевірте вхід, строки, вільні місця та попередню реєстрацію.

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

Recommendations match interest topics rather than repeated-word frequency. Administrators manage bilingual topics and additional aliases through the website. Selected interests take priority; registration and reading topics are used when explicit topics are absent. No topical signal means no recommendations. This is a deterministic topic algorithm, not a generative model. UA/EN changes the interface language. DeepL content translations are cached; original text can remain visible when translation is unavailable. Closed demonstration surveys with synthetic answers are not real research findings.

### Telegram
Open Telegram linking in your profile, select notification consent, follow your personal link and press Start. Do not share your linking link.

The bot provides events, news, profiles, messages, surveys and files. /menu opens the menu; /stop unsubscribes. Website links require a separate browser login. Administrator sessions and personal accounts have different permissions.

### Step by Step User Tasks

**Sign in and recover access.** Open the website and sign in with your email and password. Use password recovery if necessary and follow the emailed link. Keep passwords and recovery links private. Check spam or contact an administrator if the message is missing; do not create duplicate accounts.

**Edit your profile.** Enter your biography, skills, professional status, current position and organization. Select a country from the directory and specify your faculty or educational and scientific institute. Choose the specialty and code applicable to your study period. Save and check your directory entry. Profile visibility controls whether other people can find it.

Student, alumni and guest describe your relationship to the community. Professional status describes your career, not whether the account is blocked. Administrator permissions and mentoring are separate settings. A registered guest can access personal features unavailable to an anonymous visitor. A student with a valid graduation year earlier than the current year becomes an alumnus; graduation in the current year does not trigger that transition by itself.

Birth dates cannot be in the future. Graduation years must be between 1965 and the current year, no earlier than admission, and at least 15 years after birth when a birth date is supplied. Admission cannot precede birth. Omitting a birth date removes the age check, not the other date restrictions.

**Register for an event.** Open Events, search or use the calendar, read the full description and register. Check My events for the result. Cancel from the event page when cancellation is available. Deadlines and capacity may prevent registration. The QR code at the bottom opens a registration page; scanning it does not automatically register a person.

**Read news and recommendations.** Select your interests in the profile and browse news or events. Personalized recommendations use topic signals, not common connecting words. A separate text similarity algorithm also exists for event discovery. Suggestions are not a guarantee of relevance. UA/EN changes the interface; unavailable content translations can leave original text visible.

**Contact mentors and users.** Browse mentors by their skills and support areas. In Messages, find another eligible user and start a conversation. You cannot select yourself as a recipient. Availability depends on account activity, email verification, blocking and public visibility. Chats may open external group links rather than an internal group messenger. An unconfirmed mentoring label means that the displayed staff member has not confirmed participation.

**Answer surveys.** Open an available survey, complete the required answers and submit. Check the confirmation. Results depend on survey settings; closed surveys do not accept new submissions.

### Telegram Tasks and Limits

1. Create and verify an account on the website first. Register / log in opens the website rather than completing registration inside Telegram. Automatic Telegram avatar import is not provided by this workflow.
2. Link the account using the personal link from your profile. An ordinary `/start` without linking does not grant personal account access.
3. Open `/menu` and choose news, events or another available action. Some buttons open website pages requiring a separate browser login.
4. Propose news with `/submit_news Title`, followed by the article text on a new line. Maximum title length is 200 characters, body length 10000; up to three proposals per hour are allowed. Submissions await moderation rather than publishing automatically.
5. Use the file submission menu for files. The limit is 20 MB. Telegram files may be stored as Telegram references and identifiers rather than downloaded server copies.
6. Change notification consent in your profile or use `/stop` to unsubscribe.

The bot responds while the server application and its Telegram worker are running. Pressing Start does not start the server. If it does not respond, the server operator checks the container and logs; users do not need a local bot process.

### Administration
Use the administrator login with privately supplied credentials. Administrators manage events, news, accounts, surveys, files and analytics. Daily KPI imports enter a review queue rather than publishing automatically. Review text, translations, images and generated short descriptions before publication.

In bot administration, check connection status, select only consenting recipients and inspect delivery results. Acceptance by Telegram does not prove that a message was read.

### Step by Step Administrator Tasks

1. **News:** create an article or open a Telegram proposal. Review its title, text, translation and image. Generate and review the short description before publishing. Automatic summaries select source text; they are not guaranteed editorial rewrites.
2. **Events:** enter the title, description, date, venue, topic and registration limits. Save and check the public page using an ordinary account. Website registration and available bot actions share application data.
3. **Users:** find the correct account and check its role, professional status, activity and email verification. Grant permissions only to authorized people. Verify the selected account before blocking or deleting it.
4. **Administrator delegation:** grant rights through user management without editing code. Active administrators with verified email can link their own Telegram through a personal one-time link. Linking Telegram does not sign them into the browser administration area.
5. **Directories:** add a specialty code, bilingual names and applicable period. The same specialty can have codes from before 2015, from 2015–2024 and after 2024. Do not replace every historical graduate code with a current code. Countries use the shared code and name directory.
6. **Broadcasts:** check bot connectivity, prepare the message, select consenting recipients, review the recipient count and send. Inspect delivery results and errors. Do not blindly resend when the previous outcome is uncertain.
7. **Surveys and files:** review survey questions and deadlines before opening participation; manage results and moderated files through their respective sections.

### Server Checks and Troubleshooting

In PuTTY, select SSH, enter `77.47.192.6` and port `22`, then use your assigned server account. Never publish the server password, bot token or email credentials in README or GitHub.

The server operator can check service health:

```sh
docker ps --filter name=alumnixhub-std19
docker logs --tail 100 alumnixhub-std19
curl -I http://127.0.0.1:4063/
```

Restart only when necessary after reviewing the logs:

```sh
docker restart alumnixhub-std19
```

Preserve the data directory, uploads and `.env` during upgrades. Follow the maintenance guide for backups. The agreed daily backup retention is the latest 14 archives when the mechanism is configured; a retention rule alone does not verify backup creation or restoration.

- **403:** check your permissions and the appropriate administrator login.
- **Silent bot:** check server health, account linking and logs. Do not run a second worker with the same token.
- **Missing email:** check spam, the address and mail settings. Diagnostic recovery paths can expose operational links; keep them private.
- **Missing search recipient:** check the name, language, public visibility and account state. Your own account is not a new conversation recipient.
- **Rejected dates:** check the chronology of birth, admission and graduation.
- **Rejected event registration:** check login, deadlines, capacity and an existing registration.

### Server and Database
The website runs on the university server independently of a laptop. Public port: **4063**. PuTTY uses host 77.47.192.6, SSH port **22**, username std19.

The alumnixhub-std19 container runs the website and Telegram worker. Internal port 8000 maps to public port 4063. Closing PuTTY leaves it running. Do not run a competing local worker for the same bot.

SQLite lives at /home/std19/alumnixhub/data/dev.db, mounted as /data/dev.db. Container restarts and source updates preserve the database and the separate uploads directory. Laptop and server databases do not synchronize automatically.

There is no fixed account limit in the application. The file grows with records, messages and analytics, but storage does not expand automatically. SQLite permits one writer at a time: stored account capacity is not concurrent visitor capacity. Use PostgreSQL for substantial write-heavy workloads.

The current HTTP endpoint does not encrypt traffic. A domain and HTTPS are needed for secure public production use.

[Maintenance and backups](DEPLOYMENT.md) · [JMeter test and results](tests/performance/README.md)
