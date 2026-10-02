# University server

Public website: http://77.47.192.6:4063/

In PuTTY, enter host `77.47.192.6`, SSH port `22`, and login `std19`.
Port `4063` is the website port; it is not the SSH port.
Use the server password supplied by the university. It is not stored in this repository.

The observed SSH server key is:

`ssh-ed25519 SHA256:KDR8aRwTxCGG5+j6taP01bvA/C9xoIdoq5/iF3rG2sg`

The application runs in Docker as `alumnixhub-std19`. Its automatic restart policy keeps
the website and Telegram workers available after you close PuTTY and after Docker restarts.
Do not start a second Telegram polling worker for the same bot token.

Useful commands after logging in:

```bash
docker ps --filter name=alumnixhub-std19
docker logs --tail 100 alumnixhub-std19
docker restart alumnixhub-std19
```

Project directory: `/home/std19/alumnixhub/source`.
Persistent data: `/home/std19/alumnixhub/data`.
Uploads: `/home/std19/alumnixhub/uploads`.
Private settings: `/home/std19/alumnixhub/.env`.
The database and administrator credentials are excluded from Git and the Docker image.

The transferred database contains the current local content and test accounts. Their
login details remain in the private local `backups/test-accounts.md` file. Source code
transfers do not publish databases or credentials to GitHub.
