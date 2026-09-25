import sqlite3
from flask import Blueprint, request, jsonify
from db import query, execute, executemany, now, parse_pagination
from auth import require_auth, require_admin, get_user, get_role

bp = Blueprint("publishers", __name__)

VALID_MARKETS = {"IT", "ES", "FR", "UK", "PT"}
TIER_MAP = [(70, "top"), (40, "mid"), (0, "low")]


def compute_tier(dr):
    if dr is None:
        return "low"
    try:
        for t, label in TIER_MAP:
            if int(dr) >= t:
                return label
        return "low"
    except (ValueError, TypeError):
        return "low"


def _build_publisher(row, with_relations=False):
    p = dict(row)
    p["tier"] = compute_tier(p.get("dr"))
    if not with_relations:
        return p
    pid = p["id"]
    p["journalists"] = query(
        "SELECT id, email, first_name, last_name, response_status, enrichment_status FROM journalists WHERE publisher_id=? AND deleted_at IS NULL ORDER BY last_name",
        (pid,)
    )
    p["campaigns"] = query(
        """SELECT DISTINCT c.id, c.name FROM campaigns c
           JOIN journalist_campaigns jc ON jc.campaign_id=c.id
           JOIN journalists j ON j.id=jc.journalist_id
           WHERE j.publisher_id=? AND c.deleted_at IS NULL""",
        (pid,)
    )
    p["topics"] = query(
        """SELECT DISTINCT t.name FROM topics t
           JOIN journalist_topics jt ON jt.topic_id=t.id
           JOIN journalists j ON j.id=jt.journalist_id
           WHERE j.publisher_id=? ORDER BY t.name""",
        (pid,)
    )
    return p


def _log_audit(entity_id, action, user, role, fields=None):
    if not fields:
        execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('publisher',?,?,?,?)",
            (entity_id, action, user, role)
        )
        return
    rows = [
        ("publisher", entity_id, action, field,
         str(old) if old is not None else None,
         str(new) if new is not None else None,
         user, role)
        for field, (old, new) in fields.items()
    ]
    executemany(
        "INSERT INTO audit_log (entity_type, entity_id, action, field, old_value, new_value, user, role) VALUES (?,?,?,?,?,?,?,?)",
        rows
    )


@bp.route("/publishers", methods=["GET"])
@require_auth
def list_publishers():
    market = request.args.get("market", "").upper()
    tier = request.args.get("tier", "")
    search = request.args.get("search", "").strip()
    include_deleted = request.args.get("include_deleted") == "1"
    limit, offset = parse_pagination(request.args, default_limit=200, max_limit=1000)

    conditions = []
    params = []

    if not include_deleted:
        conditions.append("deleted_at IS NULL")
    if market:
        conditions.append("market=?")
        params.append(market)
    if tier:
        if tier == "top":
            conditions.append("dr >= 70")
        elif tier == "mid":
            conditions.append("dr >= 40 AND dr < 70")
        elif tier == "low":
            conditions.append("(dr IS NULL OR dr < 40)")
    if search:
        conditions.append("(name LIKE ? OR domain LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(
        f"SELECT * FROM publishers {where} ORDER BY dr DESC NULLS LAST, name LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    total = query(f"SELECT COUNT(*) as n FROM publishers {where}", params, one=True)

    for r in rows:
        r["tier"] = compute_tier(r.get("dr"))

    return jsonify({"total": total["n"] if total else 0, "publishers": rows})


@bp.route("/publishers/<int:pid>", methods=["GET"])
@require_auth
def get_publisher(pid):
    row = query("SELECT * FROM publishers WHERE id=?", (pid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "publisher not found"}), 404
    return jsonify(_build_publisher(row, with_relations=True))


@bp.route("/publishers", methods=["POST"])
@require_auth
def create_publisher():
    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    name = (data.get("name") or "").strip()
    market = (data.get("market") or "").strip().upper()
    if not name:
        return jsonify({"error": "validation", "message": "name required", "field": "name"}), 400
    if market not in VALID_MARKETS:
        return jsonify({"error": "validation", "message": "market must be IT, ES or FR", "field": "market"}), 400

    existing = query("SELECT id FROM publishers WHERE lower(name)=lower(?) AND market=?", (name, market), one=True)
    if existing:
        return jsonify({"error": "conflict", "message": "publisher already exists"}), 409

    dr = data.get("dr")
    try:
        dr = int(dr) if dr not in (None, "") else None
        if dr is not None and not (0 <= dr <= 100):
            dr = None
    except (ValueError, TypeError):
        dr = None

    ts = now()
    try:
        pid, _ = execute(
            "INSERT INTO publishers (name, domain, dr, publisher_scope, media_group, media_type, market, region, created_at, updated_at, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                name,
                (data.get("domain") or "").strip() or None,
                dr,
                (data.get("publisher_scope") or "").strip() or None,
                (data.get("media_group") or "").strip() or None,
                (data.get("media_type") or "").strip() or None,
                market,
                (data.get("region") or "").strip() or None,
                ts, ts, user,
            )
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "conflict", "message": "publisher already exists"}), 409
    _log_audit(pid, "create", user, role)
    row = query("SELECT * FROM publishers WHERE id=?", (pid,), one=True)
    return jsonify(_build_publisher(row)), 201


@bp.route("/publishers/<int:pid>", methods=["PATCH"])
@require_auth
def update_publisher(pid):
    row = query("SELECT * FROM publishers WHERE id=?", (pid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "publisher not found"}), 404

    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    SCALAR_FIELDS = [
        "name", "domain", "dr", "publisher_scope", "media_group", "media_type", "market", "region",
        "editorial_team_url", "twitter_handle", "enrichment_last_scraped", "enrichment_source",
    ]
    changes = {}
    sets = []
    params = []

    for field in SCALAR_FIELDS:
        if field not in data:
            continue
        new_val = data[field]
        if isinstance(new_val, str):
            new_val = new_val.strip() or None
        old_val = row[field]
        if new_val != old_val:
            changes[field] = (old_val, new_val)
            sets.append(f"{field}=?")
            params.append(new_val)

    if sets:
        ts = now()
        sets += ["updated_at=?", "updated_by=?"]
        params += [ts, user, pid]
        execute(f"UPDATE publishers SET {', '.join(sets)} WHERE id=?", params)

    if changes:
        _log_audit(pid, "update", user, role, changes)

    row = query("SELECT * FROM publishers WHERE id=?", (pid,), one=True)
    return jsonify(_build_publisher(row))


@bp.route("/publishers/<int:pid>", methods=["DELETE"])
@require_auth
def delete_publisher(pid):
    row = query("SELECT id FROM publishers WHERE id=?", (pid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "publisher not found"}), 404
    user = get_user()
    role = get_role(user)
    execute("UPDATE publishers SET deleted_at=?, updated_by=? WHERE id=?", (now(), user, pid))
    _log_audit(pid, "delete", user, role)
    return jsonify({"ok": True})
