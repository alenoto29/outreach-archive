import logging
import os
import traceback
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask.json.provider import DefaultJSONProvider
from dotenv import load_dotenv

try:
    import orjson
    _HAS_ORJSON = True
except ImportError:
    _HAS_ORJSON = False

try:
    from flask_compress import Compress
    _HAS_COMPRESS = True
except ImportError:
    _HAS_COMPRESS = False

load_dotenv(Path(__file__).parent / ".env")

from db import query, now
from routes import journalists, publishers, campaigns, articles, outreach, audit, import_export

DASHBOARD_DIR = (Path(__file__).parent / ".." / "dashboard").resolve()
EXAMPLES_DIR = (Path(__file__).parent / ".." / "examples").resolve()
PUBLIC_DASHBOARD_FILES = {"index.html", "api.js", "forms.js", "csv-import.js"}

logger = logging.getLogger("outreach")


class OrjsonProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS).decode("utf-8")

    def loads(self, s, **kwargs):
        if isinstance(s, str):
            s = s.encode("utf-8")
        return orjson.loads(s)


app = Flask(__name__, static_folder=None)
if _HAS_ORJSON:
    app.json = OrjsonProvider(app)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB cap on request body (CSV import, JSON payloads)
app.config["COMPRESS_MIMETYPES"] = ["application/json", "text/html", "text/css", "text/javascript", "application/javascript"]
app.config["COMPRESS_LEVEL"] = 6
app.config["COMPRESS_MIN_SIZE"] = 500
if _HAS_COMPRESS:
    Compress(app)


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self' data:; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    return resp


@app.route("/")
def root():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/<path:filename>")
def dashboard_static(filename):
    if filename not in PUBLIC_DASHBOARD_FILES:
        return jsonify({"error": "not_found"}), 404
    full = DASHBOARD_DIR / filename
    if not full.is_file():
        return jsonify({"error": "not_found"}), 404
    return send_from_directory(DASHBOARD_DIR, filename)


@app.route("/examples/journalists-demo.csv")
def example_csv():
    return send_from_directory(EXAMPLES_DIR, "journalists-demo.csv")

app.register_blueprint(journalists.bp, url_prefix="/api")
app.register_blueprint(publishers.bp, url_prefix="/api")
app.register_blueprint(campaigns.bp, url_prefix="/api")
app.register_blueprint(articles.bp, url_prefix="/api")
app.register_blueprint(outreach.bp, url_prefix="/api")
app.register_blueprint(audit.bp, url_prefix="/api")
app.register_blueprint(import_export.bp, url_prefix="/api")


@app.route("/api/health")
def health():
    try:
        query("SELECT 1", one=True)
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "unavailable"}), 503


@app.route("/api/meta")
def meta():
    from auth import _token_valid
    if not _token_valid():
        return jsonify({"error": "unauthorized"}), 401

    rows = {}
    for market in ("IT", "ES", "FR", "UK", "PT"):
        nj = query("SELECT COUNT(*) as n FROM journalists WHERE market=? AND deleted_at IS NULL", (market,), one=True)
        np = query("SELECT COUNT(*) as n FROM publishers WHERE market=? AND deleted_at IS NULL", (market,), one=True)
        nc = query(
            """SELECT COUNT(DISTINCT jc.journalist_id) as n FROM journalist_campaigns jc
               JOIN journalists j ON j.id=jc.journalist_id WHERE j.market=? AND j.response_status != 'not answered'""",
            (market,), one=True
        )
        rows[market] = {
            "journalists": nj["n"] if nj else 0,
            "publishers": np["n"] if np else 0,
            "contacted": nc["n"] if nc else 0,
        }

    total_j = query("SELECT COUNT(*) as n FROM journalists WHERE deleted_at IS NULL", one=True)
    total_p = query("SELECT COUNT(*) as n FROM publishers WHERE deleted_at IS NULL", one=True)
    total_a = query("SELECT COUNT(*) as n FROM articles", one=True)
    total_c = query("SELECT COUNT(*) as n FROM campaigns WHERE deleted_at IS NULL", one=True)

    return jsonify({
        "total_journalists": total_j["n"] if total_j else 0,
        "total_publishers": total_p["n"] if total_p else 0,
        "total_articles": total_a["n"] if total_a else 0,
        "total_campaigns": total_c["n"] if total_c else 0,
        "per_market": rows,
        "ts": now(),
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found", "message": "endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method_not_allowed"}), 405


@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({"error": "payload_too_large", "message": "request body exceeds 10MB limit"}), 413


@app.errorhandler(500)
def internal_error(e):
    logger.error("internal error: %s\n%s", e, traceback.format_exc())
    return jsonify({"error": "internal"}), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    logger.error("unhandled exception: %s\n%s", e, traceback.format_exc())
    return jsonify({"error": "internal"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=port, debug=debug)
