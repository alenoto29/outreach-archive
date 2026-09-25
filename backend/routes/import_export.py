import csv
import hashlib
import io
import json
import re
import sqlite3
from flask import Blueprint, request, jsonify, Response
from db import query, execute, now
from auth import require_auth, require_admin, get_user, get_role

bp = Blueprint("import_export", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+$")
VALID_MARKETS = {"IT", "ES", "FR", "UK", "PT"}


def _spreadsheet_safe(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@bp.route("/export/csv", methods=["GET"])
@require_auth
def export_csv():
    export_type = request.args.get("type", "journalists")

    if export_type == "journalists":
        rows = query(
            """SELECT j.email, j.first_name, j.last_name, j.job_title,
                      p.name AS publisher, p.domain, p.dr, j.market,
                      j.email_type, j.email_status, j.response_status,
                      j.linkedin, j.author_page, j.last_contacted,
                      j.notes, j.priority, j.reports_count, j.contact_count
               FROM journalists j
               LEFT JOIN publishers p ON p.id=j.publisher_id
               WHERE j.deleted_at IS NULL
               ORDER BY j.market, p.dr DESC NULLS LAST, j.last_name"""
        )
        fieldnames = ["email", "first_name", "last_name", "job_title", "publisher", "domain", "dr",
                      "market", "email_type", "email_status", "response_status", "linkedin",
                      "author_page", "last_contacted", "notes", "priority", "reports_count", "contact_count"]
    elif export_type == "publishers":
        rows = query("SELECT * FROM publishers WHERE deleted_at IS NULL ORDER BY market, dr DESC NULLS LAST")
        fieldnames = ["name", "domain", "dr", "market", "publisher_scope", "media_group", "media_type", "region"]
    elif export_type == "campaigns":
        rows = query("SELECT * FROM campaigns WHERE deleted_at IS NULL ORDER BY market, name")
        fieldnames = ["name", "market", "date_start", "date_end"]
    else:
        return jsonify({"error": "validation", "message": "type must be journalists, publishers or campaigns"}), 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _spreadsheet_safe(row.get(key)) for key in fieldnames})

    filename = f"outreach_{export_type}_{now()[:10]}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _compute_export_etag():
    # Signature changes ONLY on actual mutations — counts + max(updated_at) across mutable entities.
    # Avoids 304 misses from meta timestamps while still invalidating on any add/edit/delete.
    parts = query(
        """SELECT
            (SELECT COUNT(*) FROM journalists WHERE deleted_at IS NULL) AS nj,
            (SELECT COUNT(*) FROM publishers WHERE deleted_at IS NULL) AS np,
            (SELECT COUNT(*) FROM campaigns WHERE deleted_at IS NULL) AS nc,
            (SELECT COUNT(*) FROM articles) AS na,
            (SELECT MAX(updated_at) FROM journalists) AS uj,
            (SELECT MAX(updated_at) FROM publishers) AS up,
            (SELECT MAX(updated_at) FROM campaigns) AS ucamp,
            (SELECT MAX(scraped_at) FROM articles) AS uart,
            (SELECT MAX(ts) FROM audit_log) AS uaud,
            (SELECT MAX(id) FROM audit_log) AS audit_id""",
        one=True
    ) or {}
    raw = "|".join(str(parts.get(k) or "") for k in ("nj","np","nc","na","uj","up","ucamp","uart","uaud","audit_id"))
    return 'W/"' + hashlib.md5(raw.encode("utf-8")).hexdigest() + '"'


@bp.route("/export/json", methods=["GET"])
@require_auth
def export_json():
    etag = _compute_export_etag()
    inm = request.headers.get("If-None-Match", "")
    if inm and inm == etag:
        resp = Response(status=304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
        return resp

    journalists = query(
        """SELECT j.*,
                  p.name AS publisher, p.domain, p.dr AS dr,
                  p.editorial_team_url AS publisher_editorial_team_url,
                  p.twitter_handle AS publisher_twitter_handle,
                  p.enrichment_last_scraped AS publisher_enrichment_last_scraped,
                  p.enrichment_source AS publisher_enrichment_source
           FROM journalists j
           LEFT JOIN publishers p ON p.id=j.publisher_id
           WHERE j.deleted_at IS NULL"""
    )

    publishers = query(
        """SELECT id, name, domain, dr, publisher_scope, media_group, media_type,
                  market, region, editorial_team_url, twitter_handle,
                  enrichment_last_scraped, enrichment_source,
                  created_at, updated_at
           FROM publishers
           WHERE deleted_at IS NULL"""
    )

    topics_by_jid = {}
    for r in query(
        "SELECT jt.journalist_id AS jid, t.name FROM journalist_topics jt JOIN topics t ON t.id=jt.topic_id"
    ):
        topics_by_jid.setdefault(r["jid"], []).append(r["name"])

    campaigns_by_jid = {}
    for r in query(
        "SELECT jc.journalist_id AS jid, c.name FROM journalist_campaigns jc JOIN campaigns c ON c.id=jc.campaign_id"
    ):
        campaigns_by_jid.setdefault(r["jid"], []).append(r["name"])

    reports_by_jid = {}
    for r in query("SELECT journalist_id AS jid, report_name FROM reports_sent"):
        reports_by_jid.setdefault(r["jid"], []).append(r["report_name"])

    for j in journalists:
        jid = j["id"]
        j["topics"] = topics_by_jid.get(jid, [])
        j["campaigns"] = campaigns_by_jid.get(jid, [])
        j["reports_sent"] = reports_by_jid.get(jid, [])

    per_market = {"IT": {"publishers": 0, "journalists": 0, "contacted": 0, "with_reports": 0, "enriched": 0},
                  "ES": {"publishers": 0, "journalists": 0, "contacted": 0, "with_reports": 0, "enriched": 0},
                  "FR": {"publishers": 0, "journalists": 0, "contacted": 0, "with_reports": 0, "enriched": 0}}
    pub_rows = query("SELECT market, COUNT(*) as n FROM publishers WHERE deleted_at IS NULL GROUP BY market")
    for r in pub_rows:
        if r["market"] in per_market:
            per_market[r["market"]]["publishers"] = r["n"]

    total_contacted = 0
    total_with_reports = 0
    total_enriched = 0
    for j in journalists:
        m = j.get("market")
        if m not in per_market:
            continue
        per_market[m]["journalists"] += 1
        if j.get("last_contacted") or (j.get("contact_count") or 0) > 0:
            per_market[m]["contacted"] += 1
            total_contacted += 1
        if j.get("reports_sent"):
            per_market[m]["with_reports"] += 1
            total_with_reports += 1
        if j.get("enrichment_status") == "enriched":
            per_market[m]["enriched"] += 1
            total_enriched += 1

    campaigns = [r["name"] for r in query(
        "SELECT name FROM campaigns WHERE deleted_at IS NULL ORDER BY name"
    )]
    topics = [r["name"] for r in query(
        "SELECT name FROM topics ORDER BY name"
    )]
    total_articles = query(
        "SELECT COUNT(*) as n FROM articles", one=True
    )["n"]

    meta = {
        "total_journalists": len(journalists),
        "total_publishers": sum(m["publishers"] for m in per_market.values()),
        "total_contacted": total_contacted,
        "total_with_reports": total_with_reports,
        "total_enriched": total_enriched,
        "total_articles": total_articles,
        "per_market": per_market,
        "all_campaigns": campaigns,
        "all_topics": topics,
        "generated": now(),
        "generated_at": now(),
    }

    resp = jsonify({"_meta": meta, "journalists": journalists, "publishers": publishers})
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    return resp


@bp.route("/import/csv", methods=["POST"])
@require_admin
def import_csv():
    user = get_user()
    role = get_role(user)
    dry_run = request.args.get("dry_run") == "1"

    if "file" not in request.files:
        return jsonify({"error": "validation", "message": "file required"}), 400

    f = request.files["file"]
    stream = f.read()
    try:
        content = stream.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = stream.decode("latin-1")

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    for i, row in enumerate(rows):
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or not EMAIL_RE.match(email):
            results["errors"].append({"row": i + 2, "msg": f"invalid email: {email!r}"})
            continue

        market = (row.get("market") or row.get("Market") or "").strip().upper()
        if market not in VALID_MARKETS:
            results["errors"].append({"row": i + 2, "msg": f"invalid market: {market!r}"})
            continue

        if dry_run:
            results["created"] += 1
            continue

        existing = query("SELECT id FROM journalists WHERE email=?", (email,), one=True)
        ts = now()

        pub_name = (row.get("publisher") or row.get("Publisher") or "").strip()
        pub_domain = (row.get("domain") or row.get("Domain") or "").strip()
        publisher_id = None
        if pub_name or pub_domain:
            name = pub_name or pub_domain
            p = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?", (name, market), one=True)
            if p:
                publisher_id = p["id"]
            else:
                try:
                    pid, _ = execute(
                        "INSERT INTO publishers (name, domain, market, created_at, updated_at, updated_by) VALUES (?,?,?,?,?,?)",
                        (name, pub_domain or None, market, ts, ts, user)
                    )
                    publisher_id = pid
                    execute(
                        "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('publisher',?,'create',?,?)",
                        (pid, user, role)
                    )
                except sqlite3.IntegrityError:
                    p = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?", (name, market), one=True)
                    publisher_id = p["id"] if p else None

        try:
            if existing:
                execute(
                    """UPDATE journalists SET first_name=?, last_name=?, publisher_id=?,
                       email_status=?, response_status=?, updated_at=?, updated_by=? WHERE email=?""",
                    (
                        (row.get("first_name") or "").strip() or None,
                        (row.get("last_name") or "").strip() or None,
                        publisher_id,
                        (row.get("email_status") or "").strip() or None,
                        (row.get("response_status") or "").strip() or None,
                        ts, user, email,
                    )
                )
                execute(
                    "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('journalist',?,'update',?,?)",
                    (existing["id"], user, role)
                )
                results["updated"] += 1
            else:
                jid, _ = execute(
                    """INSERT INTO journalists
                       (email, first_name, last_name, publisher_id, market,
                        email_status, response_status, created_at, updated_at, updated_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        email,
                        (row.get("first_name") or "").strip() or None,
                        (row.get("last_name") or "").strip() or None,
                        publisher_id, market,
                        (row.get("email_status") or "").strip() or None,
                        (row.get("response_status") or "").strip() or None,
                        ts, ts, user,
                    )
                )
                execute(
                    "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('journalist',?,'create',?,?)",
                    (jid, user, role)
                )
                results["created"] += 1
        except sqlite3.IntegrityError as e:
            msg = str(e)
            if "UNIQUE" in msg:
                results["skipped"] += 1
                results["errors"].append({"row": i + 2, "msg": "duplicate (case variant or race)"})
            elif "CHECK" in msg:
                results["errors"].append({"row": i + 2, "msg": "constraint failed"})
            else:
                raise

    if dry_run:
        results["dry_run"] = True
        results["note"] = "no changes applied"

    return jsonify(results)
