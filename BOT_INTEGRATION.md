# Diploma bot integration

## Telegram menus and worker lifecycle

Starting `py -3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
starts polling, replies/automation, and broadcast delivery automatically when
TELEGRAM_ENABLED=true. The original Aiogram process must remain stopped.
Opening Telegram does not start a stopped web server. The website's connection
screens now distinguish bot availability from whether the user's account is
linked, and update these indicators automatically while the page is open.

Plain /start now responds with a menu, even before linking. /menu and /help
show it again. Linked users can browse published news, upcoming events and
their registrations; confirm/cancel event signup; view their own profile;
find active chats matching their cohort; and submit/retrieve photos, videos
and documents. Both signup surfaces use one capacity-checked database service.
File submissions are limited to 20 MB and 10/hour. Files remain on Telegram;
the website stores opaque file IDs and metadata, not downloaded executables.
Administrators review uploads at /admin/bots/files and can request them in
their own linked Telegram account. No phone-number database is imported.

Profile editing, registration/login, private website messaging, surveys, and
administrative editing open existing authenticated website pages. The old
in-chat admin passwords, phone verification and separate limited-admin role
system are not reproduced. This implementation uses website permissions.
Website links require a public APP_BASE_URL to work on another device;
localhost links are explicitly identified as local in bot responses.

One-hour event reminders and annual birthday greetings are separately opt-in
under Profile > Telegram notifications. Birthday dates use UTC. Replies and
automated messages have persistent deduplication keys; crashes/uncertain sends
are not automatically retried. /stop revokes the link and all automation sends
recheck eligibility/consent before delivery. The single-worker deployment
constraint still applies.

Regression tests for menus, replay, signup, file isolation and reminders are
in tests/test_telegram_commands.py. External Telegram acceptance must still be
distinguished from a person reading a message.

Source: https://github.com/aletiaa/Diploma
Inspected input: user-provided Diploma-main.zip, 30 September 2026.
The ZIP was inspected without executing its code or importing its credentials/database.

## Live personal-account integration (30 September 2026)

Configure TELEGRAM_BOT_TOKEN privately in .env, TELEGRAM_ENABLED=true, and
TELEGRAM_ALLOWED_USERNAME=a_seikaaa. Never commit the token. Run exactly one
Uvicorn worker for polling, with no other polling process for this token.
The previous Aiogram application must stay stopped while this integration polls.
No webhooks are deleted or configured by the application.

Administration > Bot management > Connect my Telegram generates a hashed,
one-use linking code valid for 10 minutes. Open the resulting bot link and press
Start from the allowlisted account, then refresh the page. Only private-chat
updates from that account can consume the code. Send /stop to disconnect.
The website must remain running to receive these commands.

## Alumni subscriptions and broadcasts

Verified, active personal accounts can open Profile > Telegram notifications.
No subscription is enabled by default: users select news and/or events and
explicitly agree to receive those messages. A hashed one-use code, valid for
10 minutes, links the account after a private /start command. Unlike the admin
test account, alumni do not need an allowlisted username. A Telegram chat can
belong to only one website subscription. No existing profile handles or bot
database entries are silently enrolled.

Consent time, topics, and revocation time are stored separately from email
notification settings. Changing preferences starts a new consent timestamp.
Unsubscribe in the website or /stop clears the link, pending code and topics.
The next polling cycle processes /stop; already in-flight messages cannot be
recalled. Pending codes cannot restore a revoked subscription.

Administrators select subscribed alumni, students, or all subscribers, plus
news/events. Saving a draft does not send it. The review page shows the current
matching count and up to 50 names. Explicit confirmation queues a snapshot of
eligible recipients at that time. Repeated queue submissions are idempotent.
New subscribers are not appended to an existing queued campaign.

The background delivery worker checks account eligibility, audience, current
topic consent, chat link, consent timestamp and cancellation again immediately
before each API call. Revoked/changed subscriptions are skipped. A unique
campaign/user key prevents duplicate attempts. Queued sends can be cancelled;
already in-flight/accepted sends cannot be recalled. There are no automatic
retries. Stale sending records become unknown after two minutes to avoid
duplicating a message accepted before a process crash.

Delivery tracking shows recipient, status, completion time and Telegram message
ID. Accepted means accepted by Telegram, not read. Blocked recipients are
unsubscribed. Rate limits pause the worker for 60 seconds; affected deliveries
remain marked rate_limited. The worker is intentionally low throughput and
single-process, not a production distributed queue. Run one Uvicorn worker.

New tables are created by the existing startup bootstrap, without rewriting
existing account data. Tests mock Telegram; no test sends real announcements.
Tests: tests/test_telegram_subscriptions.py, tests/test_telegram_live.py,
tests/test_bots.py. A live multi-account acceptance test still requires volunteers
to opt in and an administrator to confirm an actual announcement.

Select My Telegram - real sending, save a draft, then Send to my Telegram.
Only the creating administrator can send that draft. Accepted means Telegram
returned a message ID, NOT that the recipient read it. Pending/unknown results
are never retried automatically because delivery may already have occurred.
Rejected/blocked/rate_limited outcomes are retained; there is currently no retry UI.
Sending is limited to the linked personal account, not real bulk audiences.
This is a new website-side Telegram API adapter, not execution of the old bot's
registration/profile/news handlers. Those handlers still need a shared data API.

## Separate offline demonstration workflows

Open Administration > Bot management (`/admin/bots`) as an administrator.
Choose an event/news item to prefill a message, review it, choose a synthetic
audience, and save a draft. Simulate sending to record a timestamp and test
recipient outcomes. Repeated simulation requests do not create extra sends.
Drafts and simulation state persist in the website database's bot_campaigns table.
The log shows the latest 50 announcements. The database retains older records.

Demo audience outcomes remain labelled simulated, not delivered. They do not
call Telegram, email, or website notifications. Real personal-account delivery
is separate from these synthetic audiences.
Website administrators are authenticated by the existing admin dependency;
state-changing forms use signed, expiring administrator-bound CSRF tokens.

## Existing bot compatibility

The provided bot uses Aiogram polling, SQLite users, and JSON event storage.
`/admin/bots/events.json` exports public event fields matching
`BOT/handlers/events/utils/event_utils.py`: id, title, description, datetime,
max_seats, available_seats. Website registration counts determine available seats.
This is a one-way export, NOT automatic synchronization. Do not overwrite a live
bot's events.json: its IDs/registrations may differ. Back up and reconcile IDs
before importing into an isolated bot test instance.

## Wider production rollout: still required

1. Rotate any bot token/admin secret that was committed to the source repository.
   Exclude .env, alumni.db, administrator files, and user exports from Git.
2. Choose a single authoritative event/registration database and migrate IDs.
   Avoid concurrent JSON writes and duplicate independent seat counters.
3. Add authenticated bot-to-web API access with narrowly scoped credentials.
4. Link Telegram accounts through expiring one-use tokens and user opt-in;
   never infer chat IDs from names, phone numbers, or Telegram handles.
5. Add a real asynchronous delivery worker with Telegram rate limiting,
   retry/backoff, deduplication, blocked-user handling, and auditable outcomes.
6. Run either polling or webhooks, not both, with process supervision.
7. Validate real delivery in a dedicated test bot before enabling production.

## Acceptance cases for the diploma / OpenProject

- Guest/non-admin cannot view the workspace, export, create, or simulate.
- Missing, forged, expired, or another admin's CSRF token is rejected.
- Blank/oversized messages and invalid audiences are rejected.
- An event or news selection produces an editable draft without sending.
- Simulation includes only the selected synthetic audience.
- Repeating simulation preserves the original completion timestamp.
- Message HTML is escaped, never executed.
- Export matches the bot event schema and contains no alumni contact data.
- Ukrainian/English labels, narrow layouts, and empty logs remain usable.

Automated backend coverage: tests/test_bots.py.
