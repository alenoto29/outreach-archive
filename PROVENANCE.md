# Provenance and license review

License: [MIT](LICENSE), selected by Alessandro Noto for this standalone release.

- Source: an internal outreach archive, extracted into this standalone repository with a new history.
- Included source areas: the outreach archive Flask backend, SQL migrations, core API tests and dashboard shell/API/form code.
- Excluded source material: live SQLite database, CSV/JSON/JS records, contacts, article collections, graph exports, campaign history, discovery/planner outputs, previews, vendor bundles, environment files, deployment configuration and migration seeder from the legacy JSON dataset.
- Alessandro authorized publication of the adapted code. No third-party source or assets are bundled.
- Tested runtime dependencies: Flask 3.1.0 (BSD family), Gunicorn 23.0.0 (MIT) and python-dotenv 1.0.1 (BSD-3-Clause). Dev dependency pytest 8.4.2 is MIT. Tested transitives include Jinja2/Werkzeug/MarkupSafe/itsdangerous/click (Pallets BSD family), Blinker (MIT), packaging (Apache-2.0 or BSD-2-Clause), pluggy (MIT) and Pygments (BSD family). Versions and upstream license notices were inspected in the release venv; dependencies are installed upstream and not vendored. Re-check license notices for the final resolved versions before publication. No dashboard CDN bundle is included.
- No company logo, production endpoint, token, cloud configuration or real contact data is included. `examples/journalists-demo.csv` is an original fictional fixture, not a transformation of internal contacts or publishers. The browser CSV import and completeness indicator are new adaptations for this local release.

Dependencies are installed from upstream and retain their respective licenses. The MIT grant covers this repository's own code and original example data, not upstream dependencies.
