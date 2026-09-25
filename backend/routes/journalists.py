import json
import sqlite3
from flask import Blueprint, request, jsonify
from db import query, execute, executemany, now, parse_pagination, parse_int, transaction
from auth import require_auth, require_admin, get_user, get_role

bp = Blueprint("journalists", __name__)

VALID_MARKETS = {"IT", "ES", "FR", "UK", "PT"}

TIER_MAP = [
    (70, "top"),
    (40, "mid"),
    (0,  "low"),
]


def compute_tier(dr):
    if dr is None:
        return "low"
    try:
        dr = int(dr)
        for threshold, label in TIER_MAP:
            if dr >= threshold:
                return label
        return "low"
    except (ValueError, TypeError):
        return "low"


def _build_journalist(row, with_relations=False):
    j = dict(row)
    j["tier"] = compute_tier(j.get("dr"))
    if not with_relations:
        return j

    jid = j["id"]
    j["topics"] = query(
        "SELECT t.name, jt.source FROM journalist_topics jt JOIN topics t ON t.id=jt.topic_id WHERE jt.journalist_id=?",
        (jid,)
    )
    j["campaigns"] = query(
        "SELECT c.id, c.name, c.market FROM journalist_campaigns jc JOIN campaigns c ON c.id=jc.campaign_id WHERE jc.journalist_id=?",
        (jid,)
    )
    j["reports_sent"] = query(
        "SELECT id, report_name, sent_at FROM reports_sent WHERE journalist_id=? ORDER BY created_at",
        (jid,)
    )
    art_count = query("SELECT COUNT(*) as n FROM articles WHERE journalist_id=?", (jid,), one=True)
    j["articles_count"] = art_count["n"] if art_count else 0
    outreach_count = query("SELECT COUNT(*) as n FROM outreach_sends WHERE journalist_id=?", (jid,), one=True)
    j["outreach_sends_count"] = outreach_count["n"] if outreach_count else 0
    return j


def _log_audit(entity_id, action, user, role, fields=None, conn=None):
    if not fields:
        execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('journalist',?,?,?,?)",
            (entity_id, action, user, role),
            conn=conn,
        )
        return
    rows = [
        ("journalist", entity_id, action, field,
         str(old) if old is not None else None,
         str(new) if new is not None else None,
         user, role)
        for field, (old, new) in fields.items()
    ]
    executemany(
        "INSERT INTO audit_log (entity_type, entity_id, action, field, old_value, new_value, user, role) VALUES (?,?,?,?,?,?,?,?)",
        rows,
        conn=conn,
    )


@bp.route("/journalists", methods=["GET"])
@require_auth
def list_journalists():
    market = request.args.get("market")
    status = request.args.get("status")
    campaign = request.args.get("campaign")
    search = request.args.get("search", "").strip()
    limit, offset = parse_pagination(request.args, default_limit=200, max_limit=1000)
    include_deleted = request.args.get("include_deleted") == "1"

    conditions = []
    params = []

    if not include_deleted:
        conditions.append("j.deleted_at IS NULL")

    if market:
        conditions.append("j.market = ?")
        params.append(market.upper())

    if status:
        conditions.append("j.response_status = ?")
        params.append(status)

    if campaign:
        conditions.append("""j.id IN (
            SELECT jc.journalist_id FROM journalist_campaigns jc
            JOIN campaigns c ON c.id=jc.campaign_id WHERE c.name=?
        )""")
        params.append(campaign)

    if search:
        conditions.append("""(
            j.email LIKE ? OR j.first_name LIKE ? OR j.last_name LIKE ?
            OR p.name LIKE ? OR p.domain LIKE ?
        )""")
        s = f"%{search}%"
        params.extend([s, s, s, s, s])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = query(
        f"""SELECT j.*, p.name AS publisher_name, p.domain AS publisher_domain, p.dr AS dr
            FROM journalists j
            LEFT JOIN publishers p ON p.id=j.publisher_id
            {where}
            ORDER BY p.dr DESC NULLS LAST, j.last_name, j.first_name
            LIMIT ? OFFSET ?""",
        params + [limit, offset]
    )

    total = query(
        f"""SELECT COUNT(*) as n FROM journalists j
            LEFT JOIN publishers p ON p.id=j.publisher_id {where}""",
        params, one=True
    )

    for r in rows:
        r["tier"] = compute_tier(r.get("dr"))

    return jsonify({"total": total["n"] if total else 0, "journalists": rows})


@bp.route("/journalists/<int:jid>", methods=["GET"])
@require_auth
def get_journalist(jid):
    include_deleted = request.args.get("include_deleted") == "1"
    deleted_filter = "" if include_deleted else " AND j.deleted_at IS NULL"
    row = query(
        f"""SELECT j.*, p.name AS publisher_name, p.domain AS publisher_domain, p.dr AS dr,
                   p.market AS publisher_market
            FROM journalists j LEFT JOIN publishers p ON p.id=j.publisher_id
            WHERE j.id=?{deleted_filter}""",
        (jid,), one=True
    )
    if not row:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404
    return jsonify(_build_journalist(row, with_relations=True))


@bp.route("/journalists", methods=["POST"])
@require_auth
def create_journalist():
    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    raw_email = data.get("email")
    email = str(raw_email).strip() if raw_email is not None else ""
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        return jsonify({"error": "validation", "message": "valid email required", "field": "email"}), 400

    raw_market = data.get("market")
    market = str(raw_market).strip() if raw_market is not None else ""
    if market not in VALID_MARKETS:
        return jsonify({"error": "validation", "message": "market must be IT, ES or FR", "field": "market"}), 400

    existing = query("SELECT id FROM journalists WHERE email=?", (email,), one=True)
    if existing:
        return jsonify({"error": "conflict", "message": "email already exists", "field": "email"}), 409

    publisher_id = _resolve_publisher(data, market)

    ts = now()
    insert_params = (
        email,
        (data.get("first_name") or "").strip() or None,
        (data.get("last_name") or "").strip() or None,
        (data.get("job_title") or "").strip() or None,
        publisher_id,
        market,
        (data.get("email_type") or "").strip() or None,
        (data.get("email_status") or "").strip() or None,
        (data.get("response_status") or "").strip() or None,
        (data.get("linkedin") or "").strip() or None,
        (data.get("author_page") or "").strip() or None,
        (data.get("twitter") or "").strip() or None,
        (data.get("phone") or "").strip() or None,
        (data.get("main_topic") or "").strip() or None,
        (data.get("priority") or "").strip() or None,
        (data.get("notes") or "").strip() or None,
        (data.get("linkedin_status") or "").strip() or None,
        (data.get("contacted_by") or "").strip() or None,
        (data.get("linkedin_conversation") or "").strip() or None,
        parse_int(data.get("contact_count"), default=0),
        (data.get("authority") or "").strip() or None,
        (data.get("last_contacted") or "").strip() or None,
        None,
        0,
        ts, ts, user,
    )

    try:
        with transaction() as conn:
            jid, _ = execute(
                """INSERT INTO journalists
                   (email, first_name, last_name, job_title, publisher_id, market,
                    email_type, email_status, response_status,
                    linkedin, author_page, twitter, phone,
                    main_topic, priority, notes, linkedin_status, contacted_by,
                    linkedin_conversation, contact_count, authority,
                    last_contacted, weeks_since_contact, reports_count,
                    created_at, updated_at, updated_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                insert_params,
                conn=conn,
            )
            _sync_topics(jid, data.get("topics") or [], user, conn=conn)
            _sync_campaigns(jid, data.get("campaigns") or [], market, conn=conn)
            _log_audit(jid, "create", user, role, conn=conn)
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "UNIQUE" in msg:
            return jsonify({"error": "conflict", "message": "email already exists", "field": "email"}), 409
        if "CHECK" in msg:
            return jsonify({"error": "validation", "message": "constraint failed", "field": "email"}), 400
        raise

    row = query(
        "SELECT j.*, p.name AS publisher_name, p.domain AS publisher_domain, p.dr AS dr FROM journalists j LEFT JOIN publishers p ON p.id=j.publisher_id WHERE j.id=?",
        (jid,), one=True
    )
    return jsonify(_build_journalist(row, with_relations=True)), 201


@bp.route("/journalists/<int:jid>", methods=["PATCH"])
@require_auth
def update_journalist(jid):
    row = query("SELECT * FROM journalists WHERE id=?", (jid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404

    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    SCALAR_FIELDS = [
        "email", "first_name", "last_name", "job_title", "market",
        "email_type", "email_status", "response_status",
        "linkedin", "author_page", "twitter", "phone",
        "main_topic", "priority", "notes", "linkedin_status", "contacted_by",
        "linkedin_conversation", "contact_count", "authority",
        "last_contacted", "weeks_since_contact", "reports_count",
        "enrichment_status", "enrichment_last_scraped", "enrichment_bio",
        "years_exp", "last_article_date", "articles_count_6m",
        "expertise_tags", "enrichment_source",
    ]

    changes = {}
    sets = []
    params = []

    for field in SCALAR_FIELDS:
        if field not in data:
            continue
        new_val = data[field]
        if field == "expertise_tags" and isinstance(new_val, (list, dict)):
            new_val = json.dumps(new_val)
        if isinstance(new_val, str):
            new_val = new_val.strip() or None
        old_val = row[field]
        if new_val != old_val:
            changes[field] = (old_val, new_val)
            sets.append(f"{field}=?")
            params.append(new_val)

    if "publisher_domain" in data or "publisher_name" in data:
        pub_id = _resolve_publisher(data, row["market"])
        if pub_id != row["publisher_id"]:
            changes["publisher_id"] = (row["publisher_id"], pub_id)
            sets.append("publisher_id=?")
            params.append(pub_id)

    with transaction() as conn:
        if sets:
            ts = now()
            sets += ["updated_at=?", "updated_by=?"]
            params += [ts, user, jid]
            execute(f"UPDATE journalists SET {', '.join(sets)} WHERE id=?", params, conn=conn)

        if "topics" in data:
            _sync_topics(jid, data["topics"], user, conn=conn)
        if "campaigns" in data:
            _sync_campaigns(jid, data["campaigns"], row["market"], conn=conn)

        if changes:
            _log_audit(jid, "update", user, role, changes, conn=conn)

    row = query(
        "SELECT j.*, p.name AS publisher_name, p.domain AS publisher_domain, p.dr AS dr FROM journalists j LEFT JOIN publishers p ON p.id=j.publisher_id WHERE j.id=?",
        (jid,), one=True
    )
    return jsonify(_build_journalist(row, with_relations=True))


@bp.route("/journalists/<int:jid>", methods=["DELETE"])
@require_auth
def delete_journalist(jid):
    row = query("SELECT id, deleted_at FROM journalists WHERE id=?", (jid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404

    user = get_user()
    role = get_role(user)

    hard = request.args.get("hard") == "1"
    if hard and role != "admin":
        return jsonify({"error": "forbidden", "message": "hard delete requires admin"}), 403

    if hard:
        execute("DELETE FROM journalists WHERE id=?", (jid,))
    else:
        execute("UPDATE journalists SET deleted_at=?, updated_by=? WHERE id=?", (now(), user, jid))

    _log_audit(jid, "delete", user, role)
    return jsonify({"ok": True, "hard": hard})


@bp.route("/journalists/<int:jid>/restore", methods=["POST"])
@require_admin
def restore_journalist(jid):
    row = query("SELECT id FROM journalists WHERE id=?", (jid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404
    user = get_user()
    role = get_role(user)
    execute("UPDATE journalists SET deleted_at=NULL, updated_by=?, updated_at=? WHERE id=?", (user, now(), jid))
    _log_audit(jid, "restore", user, role)
    return jsonify({"ok": True})


ENRICH_SOURCE = "candidate-import"


@bp.route("/journalists/enrich", methods=["POST"])
@require_auth
def enrich_journalists():
    """Optional idempotent import of user-supplied candidate records.
    Dedup per email O nome+cognome -> SKIP se gia presente (mai UPDATE, non tocca il curato a mano).
    Marks enrichment_source=candidate-import; created_at is the insertion time. Idempotent.
    Body: {"candidates": [ {email, market, first_name, last_name, publisher, topics, ...}, ... ]}
    """
    data = request.get_json(silent=True) or {}
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return jsonify({"error": "validation", "message": "candidates must be a list"}), 400

    user = get_user()
    role = get_role(user)
    results = {"created": 0, "skipped": 0, "errors": []}

    for i, c in enumerate(candidates):
        if not isinstance(c, dict):
            results["errors"].append({"index": i, "msg": "candidate must be an object"})
            continue
        email = str(c.get("email") or "").strip()
        if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
            results["errors"].append({"index": i, "msg": f"invalid email: {email!r}"})
            continue
        market = str(c.get("market") or "").strip().upper()
        if market not in VALID_MARKETS:
            results["errors"].append({"index": i, "msg": f"invalid market: {market!r}"})
            continue

        first = (c.get("first_name") or "").strip()
        last = (c.get("last_name") or "").strip()

        # Dedup pre-insert: email OR nome+cognome (case-insensitive). Skip, mai UPDATE.
        dup = query("SELECT id FROM journalists WHERE lower(email)=lower(?)", (email,), one=True)
        if not dup and first and last:
            dup = query(
                "SELECT id FROM journalists WHERE lower(first_name)=lower(?) AND lower(last_name)=lower(?)",
                (first, last), one=True,
            )
        if dup:
            results["skipped"] += 1
            continue

        ts = now()
        try:
            with transaction() as conn:
                publisher_id = _resolve_publisher(c, market, conn=conn)
                jid, _ = execute(
                    """INSERT INTO journalists
                       (email, first_name, last_name, job_title, publisher_id, market,
                        email_type, author_page, linkedin, twitter, main_topic, notes,
                        enrichment_source, enrichment_last_scraped,
                        contact_count, reports_count, created_at, updated_at, updated_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        email, first or None, last or None,
                        (c.get("job_title") or "").strip() or None,
                        publisher_id, market,
                        (c.get("email_type") or "").strip() or None,
                        (c.get("author_page") or "").strip() or None,
                        (c.get("linkedin") or "").strip() or None,
                        (c.get("twitter") or "").strip() or None,
                        (c.get("main_topic") or "").strip() or None,
                        (c.get("notes") or "").strip() or None,
                        ENRICH_SOURCE, ts,
                        0, 0, ts, ts, user,
                    ),
                    conn=conn,
                )
                _sync_topics(jid, c.get("topics") or [], user, conn=conn)
                _sync_campaigns(jid, c.get("campaigns") or [], market, conn=conn)
                _log_audit(jid, "create", user, role, conn=conn)
            results["created"] += 1
        except sqlite3.IntegrityError as e:
            # Race: email UNIQUE colpita tra il check e l'insert -> skip pulito.
            if "UNIQUE" in str(e):
                results["skipped"] += 1
            else:
                results["errors"].append({"index": i, "msg": "constraint failed"})

    return jsonify(results)


def _resolve_publisher(data, market, conn=None):
    pub_name = (data.get("publisher_name") or data.get("publisher") or "").strip()
    pub_domain = (data.get("publisher_domain") or data.get("domain") or "").strip()
    if not pub_name and not pub_domain:
        return None
    name = pub_name or pub_domain
    row = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?", (name, market), one=True, conn=conn)
    if row:
        return row["id"]
    ts = now()
    try:
        pid, _ = execute(
            "INSERT INTO publishers (name, domain, market, created_at, updated_at, updated_by) VALUES (?,?,?,?,?,?)",
            (name, pub_domain or None, market, ts, ts, "auto"), conn=conn,
        )
    except sqlite3.IntegrityError:
        row = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?", (name, market), one=True, conn=conn)
        if row:
            return row["id"]
        raise
    execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('publisher',?,'create','auto','auto')",
        (pid,), conn=conn,
    )
    return pid


def _sync_topics(journalist_id, topics, user, conn=None):
    for t in topics:
        t_name = (t if isinstance(t, str) else t.get("name", "")).strip()
        if not t_name:
            continue
        source = (t.get("source", "manual") if isinstance(t, dict) else "manual")
        row = query("SELECT id FROM topics WHERE lower(name)=lower(?)", (t_name,), one=True, conn=conn)
        if row:
            tid = row["id"]
        else:
            tid, _ = execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (t_name,), conn=conn)
            if not tid:
                tid = query("SELECT id FROM topics WHERE lower(name)=lower(?)", (t_name,), one=True, conn=conn)["id"]
        execute(
            "INSERT OR IGNORE INTO journalist_topics (journalist_id, topic_id, source) VALUES (?,?,?)",
            (journalist_id, tid, source),
            conn=conn,
        )


def _sync_campaigns(journalist_id, campaigns, market, conn=None):
    for c in campaigns:
        c_name = (c if isinstance(c, str) else c.get("name", "")).strip()
        if not c_name:
            continue
        row = query(
            "SELECT id FROM campaigns WHERE lower(name)=lower(?) AND market=? AND deleted_at IS NULL",
            (c_name, market), one=True, conn=conn,
        )
        if row:
            cid = row["id"]
        else:
            ts = now()
            try:
                cid, _ = execute(
                    "INSERT INTO campaigns (name, market, created_at, updated_at, updated_by) VALUES (?,?,?,?,?)",
                    (c_name, market, ts, ts, "auto"),
                    conn=conn,
                )
            except sqlite3.IntegrityError:
                row = query(
                    "SELECT id FROM campaigns WHERE lower(name)=lower(?) AND market=? AND deleted_at IS NULL",
                    (c_name, market), one=True, conn=conn,
                )
                if not row:
                    continue
                cid = row["id"]
        execute(
            "INSERT OR IGNORE INTO journalist_campaigns (journalist_id, campaign_id) VALUES (?,?)",
            (journalist_id, cid),
            conn=conn,
        )
