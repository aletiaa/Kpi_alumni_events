"""Inspect the university server using a pinned SSH key; prompt for its password."""
import base64
import getpass
import hashlib
import socket
import argparse
from pathlib import Path
import secrets
import sqlite3
import time
import sys

from dotenv import dotenv_values

import paramiko

HOST = "77.47.192.6"
HOST_KEY = "SHA256:KDR8aRwTxCGG5+j6taP01bvA/C9xoIdoq5/iF3rG2sg"


def connect(password=None):
    transport = paramiko.Transport(socket.create_connection((HOST, 22), timeout=20))
    transport.start_client(timeout=20)
    digest = base64.b64encode(hashlib.sha256(transport.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
    if "SHA256:" + digest != HOST_KEY:
        transport.close()
        raise RuntimeError("SSH host identity changed; verify it before continuing")
    transport.auth_password("std19", password or getpass.getpass("SSH password: "))
    client = paramiko.SSHClient()
    client._transport = transport
    return client


def run(client, command):
    _, stdout, _ = client.exec_command(command, timeout=900)
    channel = stdout.channel
    channel.set_combine_stderr(True)
    while not channel.exit_status_ready() or channel.recv_ready():
        if channel.recv_ready():
            print(channel.recv(32768).decode("utf-8", "replace"), end="", flush=True)
        else:
            time.sleep(0.2)
    status = channel.recv_exit_status()
    if status:
        raise RuntimeError(f"Remote command failed ({status})")


def deploy(client):
    from app.db import engine
    root = Path(__file__).resolve().parents[1]
    archive = root / ".pytest_cache" / "release-source.zip"
    if not archive.is_file() or engine.dialect.name != "sqlite":
        raise RuntimeError("Prepare release-source.zip and a local SQLite database first")
    snapshot = root / ".pytest_cache" / "server-data.db"
    with sqlite3.connect(engine.url.database) as source, sqlite3.connect(snapshot) as target:
        source.backup(target)
    base = "/home/std19/alumnixhub"
    run(client, "test ! -e /home/std19/alumnixhub && mkdir -m 700 /home/std19/alumnixhub && mkdir -m 700 /home/std19/alumnixhub/data /home/std19/alumnixhub/uploads && mkdir /home/std19/alumnixhub/source")
    values = {k: v for k, v in dotenv_values(root / ".env").items() if v is not None}
    values.update(DATABASE_URL="sqlite:////data/dev.db", ADMINS_CSV_PATH="/data/admins.csv",
                  APP_BASE_URL=f"http://{HOST}:4063", TELEGRAM_ENABLED="true",
                  SEED_DEMO_DATA="false", PORT="8000", SECRET_KEY=secrets.token_urlsafe(48))
    environment = "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"
    if any("\n" in str(v) or "\r" in str(v) for v in values.values()):
        raise ValueError("Multiline environment values are not supported")
    with client.open_sftp() as sftp:
        sftp.put(str(archive), base + "/release-source.zip")
        sftp.put(str(snapshot), base + "/data/dev.db")
        sftp.chmod(base + "/data/dev.db", 0o600)
        sftp.put(str(root / "admins.csv"), base + "/data/admins.csv")
        sftp.chmod(base + "/data/admins.csv", 0o600)
        with sftp.open(base + "/.env", "w") as remote:
            remote.write(environment)
        sftp.chmod(base + "/.env", 0o600)
        uploads = root / "app" / "static" / "uploads"
        if uploads.exists():
            for path in uploads.rglob("*"):
                relative = path.relative_to(uploads).as_posix()
                if path.is_dir():
                    sftp.mkdir(base + "/uploads/" + relative)
                elif path.is_file() and not path.is_symlink():
                    sftp.put(str(path), base + "/uploads/" + relative)
    run(client, "python3 -m zipfile -e /home/std19/alumnixhub/release-source.zip /home/std19/alumnixhub/source")
    run(client, "docker build -t alumnixhub-std19:release /home/std19/alumnixhub/source")
    run(client, "docker run -d --name alumnixhub-std19 --restart unless-stopped -p 4063:8000 --env-file /home/std19/alumnixhub/.env -v /home/std19/alumnixhub/data:/data -v /home/std19/alumnixhub/uploads:/app/app/static/uploads alumnixhub-std19:release")


def verify(client):
    run(client, "docker ps --filter name=alumnixhub-std19 --format '{{.Names}} {{.Status}} {{.Ports}}'; curl -s -o /dev/null -w 'Website HTTP: %{http_code}\\n' http://127.0.0.1:4063/; docker logs --tail 20 alumnixhub-std19")
    run(client, "docker exec alumnixhub-std19 python -c \"from app.db import SessionLocal; from app.models import TelegramState,User,Event,News; db=SessionLocal(); s=db.get(TelegramState,1); print('Telegram:',s.status if s else 'not_checked'); print('Users:',db.query(User).count(),'Mentors:',db.query(User).filter_by(is_mentor=True).count(),'Events:',db.query(Event).count(),'News:',db.query(News).count()); db.close()\"")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect-docker", action="store_true")
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--password-stdin", action="store_true", help="Read a password from a private input pipe")
    parser.add_argument("--resume", action="store_true", help="Build and start the already uploaded release")
    parser.add_argument("--update-source", action="store_true", help="Update application source, retaining server data and secrets")
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else None
    with connect(password) as client:
        if args.update_source:
            archive = Path(__file__).resolve().parents[1] / ".pytest_cache" / "release-source.zip"
            with client.open_sftp() as sftp:
                sftp.put(str(archive), "/home/std19/alumnixhub/release-source.zip")
            run(client, "python3 -m zipfile -e /home/std19/alumnixhub/release-source.zip /home/std19/alumnixhub/source")
            run(client, "docker build -t alumnixhub-std19:release /home/std19/alumnixhub/source")
            run(client, "docker stop alumnixhub-std19 && docker rm alumnixhub-std19")
            run(client, "docker run -d --name alumnixhub-std19 --restart unless-stopped -p 4063:8000 --env-file /home/std19/alumnixhub/.env -v /home/std19/alumnixhub/data:/data -v /home/std19/alumnixhub/uploads:/app/app/static/uploads alumnixhub-std19:release")
        elif args.resume:
            run(client, "docker build -t alumnixhub-std19:release /home/std19/alumnixhub/source")
            run(client, "docker run -d --name alumnixhub-std19 --restart unless-stopped -p 4063:8000 --env-file /home/std19/alumnixhub/.env -v /home/std19/alumnixhub/data:/data -v /home/std19/alumnixhub/uploads:/app/app/static/uploads alumnixhub-std19:release")
        elif args.deploy:
            deploy(client)
        elif args.verify:
            verify(client)
        elif args.inspect_docker:
            run(client, "docker version --format '{{.Server.Version}}'; docker ps --filter name=alumnixhub-std19 --format '{{.Names}} {{.Status}} {{.Ports}}'; ls -la /home/std19/Kpi_alumni_events; find /home/std19/Kpi_alumni_events -maxdepth 2 -type f -name '*.db' -printf '%p %s bytes\\n'; ss -ltn | grep -E ':4063[[:space:]]' || true")
        else:
            run(client, "id; pwd; uname -a; command -v python3; python3 --version; command -v systemctl; command -v tmux; command -v docker; ls -la; ss -ltn | grep -E ':4063[[:space:]]' || true; systemctl --user is-system-running || true; loginctl show-user std19 -p Linger || true")


if __name__ == "__main__":
    main()
