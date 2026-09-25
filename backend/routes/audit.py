from flask import Blueprint, request, jsonify
from db import query, parse_pagination, parse_int
from auth import require_admin

bp = Blueprint("audit", __name__)


@bp.route("/audit", methods=["GET"])
@require_admin
def get_audit():
    entity_type = request.args.get("entity_type")
    entity_id = parse_int(request.args.get("entity_id"))
    user = request.args.get("user")
    since = request.args.get("since")
    limit, offset = parse_pagination(request.args, default_limit=100, max_limit=1000)

    conditions = []
    params = []

    if entity_type:
        conditions.append("entity_type=?")
        params.append(entity_type)
    if entity_id is not None:
        conditions.append("entity_id=?")
        params.append(entity_id)
    if user:
        conditions.append("user=?")
        params.append(user)
    if since:
        conditions.append("ts >= ?")
        params.append(since)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(
        f"SELECT * FROM audit_log {where} ORDER BY ts DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    total = query(f"SELECT COUNT(*) as n FROM audit_log {where}", params, one=True)
    return jsonify({"total": total["n"] if total else 0, "entries": rows})
