import sqlite3
from flask import Blueprint, request, jsonify
from db import query, execute, now
from auth import require_auth, get_user, get_role

bp = Blueprint("campaigns", __name__)

VALID_MARKETS = {"IT", "ES", "FR", "UK", "PT"}


def _log_audit(entity_id, action, user, role):
    execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('campaign',?,?,?,?)",
        (entity_id, action, user, role)
    )


@bp.route("/campaigns", methods=["GET"])
@require_auth
def list_campaigns():
    market = request.args.get("market", "").upper()
    active = request.args.get("active")

    conditions = ["deleted_at IS NULL"]
    params = []

    if market:
        conditions.append("market=?")
        params.append(market)

    where = "WHERE " + " AND ".join(conditions)
    # Single query: LEFT JOIN + GROUP BY avoids N+1 (prev: 1 COUNT per campaign).
    rows = query(
        f"""SELECT c.*, COUNT(jc.journalist_id) AS journalists_count
            FROM campaigns c
            LEFT JOIN journalist_campaigns jc ON jc.campaign_id=c.id
            {where.replace('deleted_at', 'c.deleted_at').replace('market=?', 'c.market=?')}
            GROUP BY c.id
            ORDER BY c.market, c.name""",
        params
    )

    if active == "1":
        rows = [r for r in rows if r["journalists_count"] > 0]

    return jsonify({"campaigns": rows})


@bp.route("/campaigns/<int:cid>", methods=["GET"])
@require_auth
def get_campaign(cid):
    row = query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "campaign not found"}), 404
    row = dict(row)
    row["journalists"] = query(
        """SELECT j.id, j.email, j.first_name, j.last_name, j.response_status,
                  p.name AS publisher_name, j.market
           FROM journalist_campaigns jc
           JOIN journalists j ON j.id=jc.journalist_id
           LEFT JOIN publishers p ON p.id=j.publisher_id
           WHERE jc.campaign_id=? AND j.deleted_at IS NULL
           ORDER BY p.name, j.last_name""",
        (cid,)
    )
    return jsonify(row)


@bp.route("/campaigns", methods=["POST"])
@require_auth
def create_campaign():
    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    name = (data.get("name") or "").strip()
    market = (data.get("market") or "").strip().upper()
    if not name:
        return jsonify({"error": "validation", "message": "name required", "field": "name"}), 400
    if market not in VALID_MARKETS:
        return jsonify({"error": "validation", "message": "market must be IT, ES or FR", "field": "market"}), 400

    existing = query("SELECT id FROM campaigns WHERE lower(name)=lower(?) AND market=?", (name, market), one=True)
    if existing:
        return jsonify({"error": "conflict", "message": "campaign already exists"}), 409

    ts = now()
    try:
        cid, _ = execute(
            "INSERT INTO campaigns (name, market, date_start, date_end, created_at, updated_at, updated_by) VALUES (?,?,?,?,?,?,?)",
            (
                name, market,
                (data.get("date_start") or "").strip() or None,
                (data.get("date_end") or "").strip() or None,
                ts, ts, user,
            )
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "conflict", "message": "campaign already exists"}), 409
    _log_audit(cid, "create", user, role)
    return jsonify(query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)), 201


@bp.route("/campaigns/<int:cid>", methods=["PATCH"])
@require_auth
def update_campaign(cid):
    row = query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "campaign not found"}), 404

    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    sets, params = [], []
    for field in ["name", "date_start", "date_end"]:
        if field in data:
            sets.append(f"{field}=?")
            params.append((data[field] or "").strip() or None)

    if sets:
        ts = now()
        sets += ["updated_at=?", "updated_by=?"]
        params += [ts, user, cid]
        execute(f"UPDATE campaigns SET {', '.join(sets)} WHERE id=?", params)
        _log_audit(cid, "update", user, role)

    return jsonify(query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True))


@bp.route("/campaigns/<int:cid>", methods=["DELETE"])
@require_auth
def delete_campaign(cid):
    row = query("SELECT id FROM campaigns WHERE id=?", (cid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "campaign not found"}), 404
    user = get_user()
    role = get_role(user)
    execute("UPDATE campaigns SET deleted_at=?, updated_by=? WHERE id=?", (now(), user, cid))
    _log_audit(cid, "delete", user, role)
    return jsonify({"ok": True})


@bp.route("/campaigns/<int:cid>/journalists", methods=["POST"])
@require_auth
def add_journalists_to_campaign(cid):
    row = query("SELECT id FROM campaigns WHERE id=? AND deleted_at IS NULL", (cid,), one=True)
    if not row:
        return jsonify({"error": "not_found", "message": "campaign not found"}), 404

    data = request.get_json(silent=True) or {}
    journalist_ids = data.get("journalist_ids") or []
    if not isinstance(journalist_ids, list):
        return jsonify({"error": "validation", "message": "journalist_ids must be array"}), 400

    added = 0
    for jid in journalist_ids:
        try:
            jid = int(jid)
        except (ValueError, TypeError):
            continue
        j = query("SELECT id FROM journalists WHERE id=? AND deleted_at IS NULL", (jid,), one=True)
        if not j:
            continue
        _, rowcount = execute(
            "INSERT OR IGNORE INTO journalist_campaigns (journalist_id, campaign_id) VALUES (?,?)",
            (jid, cid)
        )
        if rowcount:
            added += 1

    return jsonify({"ok": True, "added": added})
