import csv
import hashlib
import io
import json
import re
from flask import Blueprint, request, jsonify, Response
from db import query, execute, now, transaction
from auth import require_auth, require_admin, get_user, get_role

bp = Blueprint("import_export", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+$")
VALID_MARKETS = {"IT", "ES", "FR", "UK", "PT"}
IMPORT_FIELDS = {"email", "market", "first_name", "last_name", "job_title", "publisher",
                 "domain", "dr", "publisher_scope", "email_type", "email_status",
                 "response_status", "linkedin", "author_page", "last_contacted",
                 "notes", "priority", "reports_count", "contact_count", "main_topic"}
JOURNALIST_FIELDS = ("first_name", "last_name", "job_title", "email_type", "email_status",
                     "response_status", "linkedin", "author_page", "last_contacted",
                     "notes", "priority", "main_topic", "reports_count", "contact_count")


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
    if not reader.fieldnames:
        return jsonify({"error": "validation", "message": "CSV header required"}), 400
    fields = [name.strip().lower() for name in reader.fieldnames]
    if len(fields) != len(set(fields)) or not {"email", "market"}.issubset(fields):
        return jsonify({"error": "validation", "message": "unique email and market columns required"}), 400
    unknown = set(fields) - IMPORT_FIELDS
    if unknown:
        return jsonify({"error": "validation", "message": f"unsupported columns: {', '.join(sorted(unknown))}"}), 400
    reader.fieldnames = fields
    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    seen = set()

    with transaction() as conn:
        for i, raw in enumerate(reader, start=2):
            if None in raw:
                results["errors"].append({"row": i, "msg": "too many columns"})
                continue
            row = {key: (value or "").strip() for key, value in raw.items()}
            email = row["email"].lower()
            market = row["market"].upper()
            if not EMAIL_RE.match(email):
                results["errors"].append({"row": i, "msg": "invalid email"})
                continue
            if market not in VALID_MARKETS:
                results["errors"].append({"row": i, "msg": "invalid market"})
                continue
            if email in seen:
                results["skipped"] += 1
                results["errors"].append({"row": i, "msg": "duplicate email in file"})
                continue
            seen.add(email)
            try:
                dr = int(row["dr"]) if row.get("dr") else None
                counts = {k: int(row[k]) for k in ("contact_count", "reports_count") if row.get(k)}
                if (dr is not None and not 0 <= dr <= 100) or any(n < 0 for n in counts.values()):
                    raise ValueError
            except ValueError:
                results["errors"].append({"row": i, "msg": "dr must be 0-100; counts must be non-negative integers"})
                continue

            existing = query("SELECT id, market FROM journalists WHERE lower(email)=?", (email,), one=True, conn=conn)
            if existing and existing["market"] != market:
                results["errors"].append({"row": i, "msg": "existing email belongs to another market"})
                continue
            results["updated" if existing else "created"] += 1
            if dry_run:
                continue

            ts = now()
            pub_name = row.get("publisher") or row.get("domain")
            pub_id = None
            if pub_name:
                p = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?",
                          (pub_name, market), one=True, conn=conn)
                if p:
                    pub_id = p["id"]
                else:
                    pub_id, _ = execute(
                        "INSERT INTO publishers (name, market, domain, dr, publisher_scope, updated_by) VALUES (?,?,?,?,?,?)",
                        (pub_name, market, row.get("domain") or None, dr,
                         row.get("publisher_scope") or None, user), conn=conn)
                    execute("INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('publisher',?,'create',?,?)",
                            (pub_id, user, role), conn=conn)
                pub_values = {k: row[k] for k in ("domain", "publisher_scope") if row.get(k)}
                if dr is not None:
                    pub_values["dr"] = dr
                if pub_values:
                    assignments = ", ".join(f"{key}=?" for key in pub_values)
                    execute(f"UPDATE publishers SET {assignments}, updated_at=? WHERE id=?",
                            (*pub_values.values(), ts, pub_id), conn=conn)

            values = {key: counts.get(key, row[key]) for key in JOURNALIST_FIELDS if row.get(key)}
            if pub_id is not None:
                values["publisher_id"] = pub_id
            if existing:
                jid = existing["id"]
                if values:
                    assignments = ", ".join(f"{key}=?" for key in values)
                    execute(f"UPDATE journalists SET {assignments}, updated_at=?, updated_by=? WHERE id=?",
                            (*values.values(), ts, user, jid), conn=conn)
                action = "update"
            else:
                columns = ("email", "market", *values.keys(), "updated_by")
                placeholders = ", ".join("?" for _ in columns)
                jid, _ = execute(f"INSERT INTO journalists ({', '.join(columns)}) VALUES ({placeholders})",
                                 (email, market, *values.values(), user), conn=conn)
                action = "create"
            if row.get("main_topic"):
                topic_id = query("SELECT id FROM topics WHERE name=?", (row["main_topic"],), one=True, conn=conn)
                if not topic_id:
                    tid, _ = execute("INSERT INTO topics (name) VALUES (?)", (row["main_topic"],), conn=conn)
                else:
                    tid = topic_id["id"]
                execute("INSERT OR IGNORE INTO journalist_topics (journalist_id, topic_id, source) VALUES (?,?,'csv')",
                        (jid, tid), conn=conn)
            execute("INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('journalist',?,?,?,?)",
                    (jid, action, user, role), conn=conn)

    if dry_run:
        results["dry_run"] = True
        results["note"] = "no changes applied"

    return jsonify(results)
