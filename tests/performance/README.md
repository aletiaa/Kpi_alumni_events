# Apache JMeter / Навантажувальне тестування

## English
The checked-in public-browsing.jmx plan sends anonymous GET requests to six pages:
/, /events, /news, /alumni, /mentors and /surveys.

It uses five visitors, a ten-second ramp-up, five rounds and one second of think time before each request: 150 requests total. Each request must return HTTP 200. Connection timeout is five seconds; response timeout is fifteen seconds.

This is a light-load baseline, not a maximum-capacity, security, authenticated-workflow or browser rendering test. It does not run JavaScript, fetch embedded images, measure Core Web Vitals or exercise Telegram/SMTP. GET traffic still contributes to website analytics. The plan does not submit forms, send messages or register accounts. It does not maintain browser cookies, so it measures anonymous requests rather than faithful user-session analytics.

### Run
Install Java and [official Apache JMeter](https://jmeter.apache.org/download_jmeter.cgi); use CLI mode for load tests. Verify the downloaded archive using Apache's published checksum.

From the repository directory:
```powershell
py -3.11 scripts/build_jmeter_plan.py
New-Item -ItemType Directory -Force tests/performance/results
jmeter -n -t tests/performance/public-browsing.jmx -Jhost=77.47.192.6 -Jport=4063 -l tests/performance/results/run.jtl -j tests/performance/results/run.log -e -o tests/performance/results/report
```

Use a fresh result filename and an absent/empty HTML report directory for each run. Open report/index.html to inspect response times, throughput and errors. Raw results are excluded from Git.

Only test servers you are authorized to test. Do not increase concurrency on the shared university server without agreeing resource limits.

## Українська
План public-browsing.jmx виконує анонімні GET-запити до шести сторінок: головної, подій, новин, випускників, менторів та опитувань.

П'ять відвідувачів запускаються поступово за десять секунд. Кожен проходить п'ять кіл з паузою в одну секунду перед запитом: разом 150 запитів. Очікується HTTP 200; таймаути підключення й відповіді — п'ять та п'ятнадцять секунд.

Це перевірка легкого навантаження, а не максимальної місткості, безпеки або роботи авторизованих користувачів. JavaScript, зображення, відображення браузера, Telegram та SMTP не перевіряються. GET-запити потрапляють в аналітику. Форми, реєстрації та повідомлення не надсилаються. Cookies не зберігаються, тому статистика сесій не імітує реальні браузери.

Встановіть Java та офіційний JMeter, перевірте контрольну суму архіву й використайте команди вище. Для кожного запуску потрібні нові файли результатів та порожній або відсутній каталог HTML-звіту. Відкрийте report/index.html. Не збільшуйте навантаження на спільний сервер без погоджених лімітів.

## Observations / Спостереження
Measured on 2026-10-02 from a Windows computer over the public network.
Виміряно 2026-10-02 з Windows через публічну мережу.

First run: 150 requests, one read timeout on /events (0.67% errors), median 199 ms, p95 316 ms, maximum 15,231 ms. Aggregate throughput: 2.66 requests/second, including think time.
Перший запуск: 150 запитів, один таймаут /events (0,67%), медіана 199 мс, p95 316 мс, максимум 15 231 мс. Пропускна здатність з паузами: 2,66 запиту/с.

The timeout's cause is not established. Recent server logs showed HTTP 200 responses and no application exception; this does not rule out server or network delay.
Причину таймауту не встановлено. Журнал містив HTTP 200 без винятку застосунку; це не виключає затримку сервера або мережі.

Repeat run, same plan: 150 requests, zero errors, median 198.5 ms, p95 344.9 ms, maximum 433 ms. JMeter HTML aggregate throughput was 3.56 requests/second (its sampling window differs from the CLI's whole-run window). The isolated timeout did not recur, but its cause remains unresolved. Both runs together contain one failure out of 300 requests; this small sample does not establish maximum capacity or production reliability.
Повторний запуск того самого плану: 150 запитів, без помилок, медіана 198,5 мс, p95 344,9 мс, максимум 433 мс. HTML-звіт JMeter показав 3,56 запиту/с; вікно розрахунку відрізняється від загальної тривалості CLI. Таймаут не повторився, але причина не встановлена. Разом — одна помилка серед 300 запитів; це не доводить максимальну місткість чи виробничу надійність.

Machine-readable aggregate results: baseline-statistics.json and repeat-statistics.json. p95 is the time below which 95% of sampled responses completed; it includes the network path. Website HTTP 200 and Telegram connected status were confirmed after the tests.
Агреговані результати: baseline-statistics.json та repeat-statistics.json. p95 — час, у межах якого завершилися 95% відповідей, включно з мережею. Після тестів підтверджено HTTP 200 та стан Telegram connected.

At inspection, the SQLite database was 782,336 bytes with ten accounts. The shared server filesystem had approximately 330 GB free; this is not a reserved application quota or a user-capacity guarantee.
Під час перевірки SQLite займала 782 336 байтів та містила десять користувачів. На спільному диску було близько 330 ГБ вільного місця; це не квота застосунку й не гарантія місткості.

### References / Джерела
- [JMeter CLI testing](https://jmeter.apache.org/usermanual/get-started.html)
- [SQLite suitability and concurrency](https://www.sqlite.org/whentouse.html)
- [SQLite implementation limits](https://www.sqlite.org/limits.html)
