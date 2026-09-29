# Outreach archive

A local, multi-user contact archive with a Flask API, SQLite storage and a browser dashboard. A wholly fictional CSV lets you explore the archive before importing your own contacts. It does not discover contacts, send email or connect to any hosted service by default.

[View the project site](https://alenoto29.github.io/outreach-archive/). The site is a static overview; the working dashboard runs locally with the Flask API.

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

Open `http://127.0.0.1:8080` on the computer running Flask and sign in as `demo-admin` with the first token above. Go to **Database → Importa il tuo CSV**, download the example, select it and click **Controlla CSV → Conferma import**. The dashboard now shows 12 invented journalists across IT/ES/FR, six invented publishers, different contact statuses, topics and missing fields. Explore **Home** (counts and data completeness), **Database** (market/topic/status/DR filters, search, details and edits), **Publishers** (coverage), and **Entità**. The database is empty until you import; the checked-in sample CSV contains no real contact or live domain. Use one token per user. A token is mapped to a username by the server; a browser-supplied name cannot grant a role. With no valid `USER_TOKENS` mapping, all protected API routes fail closed.

For another environment, set `DB_PATH` to a new writable database path and run the initialization command against that empty path. The app binds to loopback by default. Changing the bind host makes the service reachable beyond the local machine and must be an explicit operator decision.

## Use your own CSV

1. Keep a **separate local SQLite file** for your own records (`DB_PATH`); don't edit or commit `examples/journalists-demo.csv` with real contacts. The `.gitignore` excludes `*.sqlite` and `.env`.
2. Prepare a comma-separated UTF-8 CSV with `email,market` headers (UTF-8 BOM and Latin-1 also accepted). A full template is [`examples/journalists-demo.csv`](examples/journalists-demo.csv). Supported markets: `IT`, `ES`, `FR`, `UK`, `PT`. Required per row: valid unique email and market. Optional headers: `first_name,last_name,job_title,publisher,domain,dr,publisher_scope,email_type,email_status,response_status,linkedin,author_page,last_contacted,notes,priority,reports_count,contact_count,main_topic`. `dr` must be 0–100; counts must be non-negative whole numbers. Leave missing values blank. Max upload size: 10 MB per file; split larger lists into several CSVs. Header names are case-insensitive; unknown or duplicated headers are rejected.
3. Log in as an **admin**, open Database, choose the file and click **Controlla CSV**. The preview shows how many records would be added or updated and lists invalid/duplicate row numbers, without writing anything. Fix listed errors and preview again; confirmation is enabled only if there are no errors. Click **Conferma import**; the page reloads with the imported records. Editors can browse/edit but cannot bulk-import.
4. Re-importing matches contacts by email (case-insensitive). Existing non-empty fields are updated; blank or omitted optional fields keep the previous value. Publishers are matched by name and market; `dr` belongs to the publisher. `main_topic` is added to the topic filter. Import does not verify email deliverability, infer missing facts or send messages. Existing campaigns and article metadata are managed in the UI/API, not via this CSV.

The **Completezza dei contatti** number counts records with name, surname, publisher, topic and email status present; it is a field-presence count, not a quality or deliverability score. To reset the demo, stop the server, use a new `DB_PATH` and rerun `init_db.py`. Never point it at a populated database: the initializer refuses to overwrite one.

## Features and API

- Journalist, publisher, campaign and article CRUD.
- CSV import/export, soft deletion, audit log and deterministic duplicate checks.
- SQLite transactions, WAL mode, foreign keys and busy timeout.
- Anonymous `/api/health` reports only `ok` or `unavailable` and HTTP status; it exposes no counts or error detail.
- Only the allowlisted dashboard files (`index.html`, `api.js`, `forms.js`, `csv-import.js`) and fictional example CSV are served. Legacy data dumps, graph artifacts, history, preview pages and crawler results are absent.
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

- This package is for local archive use. It contains no production URL, cloud deployment file, credentials, real contact records or seed database; the CSV example is invented from scratch.
- Do not expose it to a network without TLS termination, secret management, rate limiting, suitable session/token lifecycle and deployment-specific security review.
- The included identity contract assumes trusted operator-managed per-user tokens. Tokens are plaintext bearer secrets in process environment and per-tab browser session storage; they are not hashed server-side and are not protected from same-origin script compromise.
- Audit logs and contacts are stored in SQLite. The project does not encrypt the database at rest or implement retention/backup automation.
- No container is distributed. Container build, content and architecture are therefore not claimed or tested.

## Provenance and AI assistance

Backend and UI code are an extraction/adaptation of Alessandro Noto's internal archive workflow. AI assistance was used during packaging and hardening. This release has not been deployed or tested against any hosted service. MIT licensed; see [`LICENSE`](LICENSE) and [`PROVENANCE.md`](PROVENANCE.md).
