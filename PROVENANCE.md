# Provenance and license review

Status: **not cleared for public release**. No license has been selected or added.

- Source repository baseline: private `pursuance-hub` commit `c652513518363d1d11fce1953bbf7bc43f149cfe`.
- Included source areas: the outreach archive Flask backend, SQL migrations, core API tests and dashboard shell/API/form code.
- Excluded source material: live SQLite database, CSV/JSON/JS records, contacts, article collections, graph exports, campaign history, discovery/planner outputs, previews, vendor bundles, environment files, deployment configuration and migration seeder from the legacy JSON dataset.
- Code publication authorization is recorded in the private release plan. It does not establish rights to third-party code/assets or select a license for this repository.
- Tested runtime dependencies: Flask 3.1.0 (BSD family), Gunicorn 23.0.0 (MIT) and python-dotenv 1.0.1 (BSD-3-Clause). Dev dependency pytest 8.4.2 is MIT. Tested transitives include Jinja2/Werkzeug/MarkupSafe/itsdangerous/click (Pallets BSD family), Blinker (MIT), packaging (Apache-2.0 or BSD-2-Clause), pluggy (MIT) and Pygments (BSD family). Versions and upstream license notices were inspected in the release venv; dependencies are installed upstream and not vendored. Re-check license notices for the final resolved versions before publication. No dashboard CDN bundle is included.
- No company logo, production endpoint, token, cloud configuration or real contact data is included.

Before publication, review the final source and history, verify dependency notices/licenses, select a repository license, and approve the exact commit. This file is an audit record, not a license grant.
