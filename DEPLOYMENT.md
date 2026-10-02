# University Server / Університетський сервер

Website / Сайт: http://77.47.192.6:4063/

## Connection / Підключення
PuTTY: host 77.47.192.6, SSH port **22**, username std19. Website port **4063**, container internal port 8000.
SSH fingerprint:
```text
SHA256:KDR8aRwTxCGG5+j6taP01bvA/C9xoIdoq5/iF3rG2sg
```

| Location / Шлях | Purpose / Призначення |
| --- | --- |
| /home/std19/alumnixhub/source | Application source / Код |
| /home/std19/alumnixhub/.env | Private settings / Приватні налаштування |
| /home/std19/alumnixhub/data/dev.db | Persistent SQLite / Постійна база |
| /home/std19/alumnixhub/data/admins.csv | Private hashed administrator credentials / Хешовані облікові дані |
| /home/std19/alumnixhub/uploads | Uploaded files / Завантажені файли |

Never publish settings, databases, administrator files or backups.
Не публікуйте налаштування, бази, адміністративні файли або резервні копії.

## Status / Стан
```sh
docker ps --filter name=alumnixhub-std19
docker logs --tail 80 alumnixhub-std19
docker stats --no-stream alumnixhub-std19
curl -I http://127.0.0.1:4063/
docker restart alumnixhub-std19
```

Restart policy: unless-stopped. The website starts the Telegram worker; do not run another worker for the same token.
Політика перезапуску: unless-stopped. Сайт запускає Telegram; не запускайте другий обробник.

## Updates / Оновлення
Repository: https://github.com/2026-TV-52mp/Seikauskaite_AA

Upload a source archive through SFTP and extract into source. Build successfully before stopping the current container. Preserve .env, data and uploads.
Завантажте архів коду через SFTP та розпакуйте у source. Спочатку успішно зберіть образ. Збережіть .env, data й uploads.

```sh
docker build -t alumnixhub-std19:release /home/std19/alumnixhub/source
docker stop alumnixhub-std19
docker rm alumnixhub-std19
docker run -d --name alumnixhub-std19 --restart unless-stopped -p 4063:8000 --env-file /home/std19/alumnixhub/.env -v /home/std19/alumnixhub/data:/data -v /home/std19/alumnixhub/uploads:/app/app/static/uploads alumnixhub-std19:release
```

The optional scripts/deploy_university.py --update-source helper preserves server data and requires Paramiko. --deploy is for initial installation only.
Допоміжний scripts/deploy_university.py --update-source зберігає дані та потребує Paramiko. --deploy — лише для першого встановлення.

## Backups / Резервні копії
Use SQLite's backup API for a consistent live backup:
Використовуйте SQLite backup API для узгодженої копії:

```sh
docker exec alumnixhub-std19 python -c "import sqlite3,datetime; p='/data/backup-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.db'; a=sqlite3.connect('/data/dev.db'); b=sqlite3.connect(p); a.backup(b); b.close(); a.close(); print(p)"
```

The backup appears in the server data directory. Download privately over SFTP. Back up uploads and settings separately; test restoration using a separate database.
Копія з'явиться у data. Завантажте приватно через SFTP. Окремо збережіть uploads та налаштування; перевіряйте відновлення на окремій базі.

HTTP does not encrypt browser traffic. Configure a domain, TLS certificate and reverse proxy for secure public use.
HTTP не шифрує трафік. Для захищеного використання потрібні домен, TLS-сертифікат та зворотний проксі.
