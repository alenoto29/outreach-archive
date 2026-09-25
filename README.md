# Outreach archive

A local, multi-user contact archive with a Flask API, SQLite storage and a small browser dashboard. It does not discover contacts, send email or connect to any hosted service by default.

## Local quickstart

Requirements: Python 3.10+.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
python3 backend/scripts/init_db.py --db /tmp/outreach-archive-demo.sqlite
```

Create individual throwaway tokens for the local demo. Configure the same environment in the server process:

```bash
export DB_PATH=/tmp/outreach-archive-demo.sqlite
export USER_TOKENS='demo-admin:replace-with-a-random-local-token,demo-editor:replace-with-another-random-local-token'
export ADMIN_NAMES=demo-admin
python3 backend/app.py
```

Open <http://127.0.0.1:8080>. Use one token per user. A token is mapped to a username by the server; a browser-supplied name cannot grant a role. With no valid `USER_TOKENS` mapping, all protected API routes fail closed. The included database is created empty; no contact seed data is bundled.

For another environment, set `DB_PATH` to a new writable database path and run the initialization command against that empty path. The app binds to loopback by default. Changing the bind host makes the service reachable beyond the local machine and must be an explicit operator decision.

## Features and API

- Journalist, publisher, campaign and article CRUD.
- CSV import/export, soft deletion, audit log and deterministic duplicate checks.
- SQLite transactions, WAL mode, foreign keys and busy timeout.
- Anonymous `/api/health` reports only `ok` or `unavailable` and HTTP status; it exposes no counts or error detail.
- Only the allowlisted dashboard files (`index.html`, `api.js`, `forms.js`) are served. Legacy data dumps, graph artifacts, history, preview pages and crawler results are absent.
- API credentials use the `Authorization: Bearer` header, never URL query strings. The browser keeps the token in `sessionStorage`; closing the tab clears it. Revoke by removing that user's token from `USER_TOKENS` and restarting the server.
- CSV export neutralizes cells beginning with spreadsheet formula characters. ETags include the audit sequence so rapid same-second writes invalidate caches.

## Tests and recovery

```bash
cd backend
python3 -m pytest tests/ -q
```

The tests build isolated temporary databases and use invented contacts. `tests/test_local_setup.py` verifies distinct DB paths plus a SQLite backup/restore round-trip. Do not point test `DB_PATH` at a user database.

To back up a stopped local database, copy it using SQLite's backup API or `sqlite3 .backup`; restore to a new path, verify integrity and schema, then point `DB_PATH` at the restored file. The test demonstrates the mechanism only and is not an operational backup schedule.

## Security and deployment limits

- This package is for local archive use. It contains no production URL, cloud deployment file, credentials, real contact records or seed database.
- Do not expose it to a network without TLS termination, secret management, rate limiting, suitable session/token lifecycle and deployment-specific security review.
- The included identity contract assumes trusted operator-managed per-user tokens. Tokens are plaintext bearer secrets in process environment and per-tab browser session storage; they are not hashed server-side and are not protected from same-origin script compromise.
- Audit logs and contacts are stored in SQLite. The project does not encrypt the database at rest or implement retention/backup automation.
- No container is distributed. Container build, content and architecture are therefore not claimed or tested.

## Provenance and AI assistance

Backend and UI code are an extraction/adaptation of Alessandro Noto's internal archive workflow. AI assistance was used during packaging and hardening. This release has not been deployed or tested against any hosted service. License selection remains pending; see [`PROVENANCE.md`](PROVENANCE.md).
