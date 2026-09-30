# Daily KPI imports

Source: https://kpi.ua/rss.xml (public RSS; no WordPress credentials).

The application checks for a due import every minute while running. A successful
import schedules the next run 24 hours later. State is stored in the database,
so a restart runs an overdue import. Failures retry after one hour; a database
lease prevents simultaneous imports across application workers.

Administrators open `/admin/kpi-import` from the dashboard or News management.
They can pause the daily schedule, run a manual import, and review each item.
Only administrators may change settings or review imported content. POST actions
require a signed, expiring form token.

Imported items are private review records, not automatically published news.
An administrator can create an unpublished news draft, explicitly publish an
event after supplying its actual start date, location and capacity, or dismiss
the item. Source URLs remain recorded even after dismissal to prevent duplicates.
RSS publication dates are never treated as event dates. Existing articles and
administrator edits are not overwritten. Imports contain titles, short excerpts,
and links to the source, not copies of complete articles or remote images.

The feed is a rolling window, not an archive; prolonged downtime can miss older
items. The importer cannot run while the computer is off or a hosting service is
asleep. For unattended daily operation use an always-on host or a hosting cron
job using the same persistent DATABASE_URL and running:

```sh
python -m app.services.kpi_import
```

Run that command hourly; the database schedule enforces the daily interval and
respects the administrator's pause setting. Exit status 1 indicates failure;
status 0 means success or not due. Do not use a separate ephemeral SQLite database
for a hosting cron job. No remote cron job or deployment is provisioned by this
change. All displayed scheduler times are UTC. Event form dates follow the
application's existing Kyiv local-time convention.

The importer accepts only KPI-hosted article links, limits response size and
item count, refuses external redirects and XML DTD/entity declarations, and
renders imported material as escaped text.
