# Release verification

- Run `py -3.11 -m pytest -q` and `node scripts/check_i18n.cjs`.
- Administrator and member passwords use salted PBKDF2-SHA256 hashes. Plaintext administrator login is no longer supported.
- Run `py -3.11 -m scripts.hash_admin_passwords` once for an existing local administrator CSV.
- Do not commit credentials, local databases, uploads, or backups.
- Demo users are not recreated on startup unless `SEED_DEMO_DATA=true` is explicitly enabled.
- Stop the application before `py -3.11 -m scripts.prepare_release_data --apply`.
  This SQLite-only command makes a consistent backup, deletes only the nine known seed accounts and their test activity, and creates closed `[DEMO]` copies of existing surveys.
- Demo survey responses are synthetic anonymous examples, not measured user feedback. Original survey answers are not augmented. The zero identified-respondent count for these anonymous examples is intentional.
- Database cleanup is local; pushing code does not copy the database to a hosting service.
- Rotate credentials previously shared in chat or stored in Git history before deployment. A new commit cannot erase historical secrets.
- Public Telegram website links require a public HTTPS `APP_BASE_URL`. Localhost links only work on the server computer.

No test suite proves the absence of every defect. Before production, verify registration email delivery, Telegram account linking, a consent-based test delivery, and database backups in the actual hosting environment.
