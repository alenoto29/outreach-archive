from flask import Blueprint, request, jsonify
from db import query, execute, now, parse_pagination, parse_int
from auth import require_auth, get_user, get_role

bp = Blueprint("outreach", __name__)


@bp.route("/outreach", methods=["GET"])
@require_auth
def list_outreach():
    journalist_id = parse_int(request.args.get("journalist_id"))
    campaign_id = parse_int(request.args.get("campaign_id"))
    since = request.args.get("since")
    limit, offset = parse_pagination(request.args, default_limit=100, max_limit=500)

    conditions = []
    params = []

    if journalist_id is not None:
        conditions.append("journalist_id=?")
        params.append(journalist_id)
    if campaign_id is not None:
        conditions.append("campaign_id=?")
        params.append(campaign_id)
    if since:
        conditions.append("sent_at >= ?")
        params.append(since)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(
        f"SELECT * FROM outreach_sends {where} ORDER BY sent_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    total = query(f"SELECT COUNT(*) as n FROM outreach_sends {where}", params, one=True)
    return jsonify({"total": total["n"] if total else 0, "sends": rows})


@bp.route("/outreach", methods=["POST"])
@require_auth
def log_send():
    data = request.get_json(silent=True) or {}
    user = get_user()
    role = get_role(user)

    journalist_id = data.get("journalist_id")
    sent_at = (data.get("sent_at") or "").strip()
    if not journalist_id:
        return jsonify({"error": "validation", "message": "journalist_id required", "field": "journalist_id"}), 400
    if not sent_at:
        return jsonify({"error": "validation", "message": "sent_at required", "field": "sent_at"}), 400

    try:
        journalist_id = int(journalist_id)
    except (ValueError, TypeError):
        return jsonify({"error": "validation", "message": "journalist_id must be integer"}), 400

    j = query("SELECT id FROM journalists WHERE id=?", (journalist_id,), one=True)
    if not j:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404

    campaign_id = data.get("campaign_id")
    if campaign_id:
        try:
            campaign_id = int(campaign_id)
            c = query("SELECT id FROM campaigns WHERE id=?", (campaign_id,), one=True)
            if not c:
                campaign_id = None
        except (ValueError, TypeError):
            campaign_id = None

    ts = now()
    oid, _ = execute(
        """INSERT INTO outreach_sends
           (journalist_id, campaign_id, strategy, email_subject, email_body, sent_at, sent_by, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            journalist_id,
            campaign_id,
            (data.get("strategy") or "").strip() or None,
            (data.get("email_subject") or "").strip() or None,
            (data.get("email_body") or "").strip() or None,
            sent_at,
            user,
            (data.get("status") or "sent").strip(),
            ts,
        )
    )

    execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, user, role) VALUES ('outreach_send',?,?,?,?)",
        (oid, "create", user, role)
    )

    return jsonify(query("SELECT * FROM outreach_sends WHERE id=?", (oid,), one=True)), 201
