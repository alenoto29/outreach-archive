import json
import sqlite3
from flask import Blueprint, request, jsonify
from db import query, execute, now
from auth import require_auth, require_admin, get_user, get_role

bp = Blueprint("articles", __name__)


def _canonical_url(url: str) -> str:
    """Mirror dashboard normalizeArticleKey: strip protocol, www., query, hash, trailing slash; lowercase."""
    if not url:
        return ""
    k = url.strip().lower()
    if k.startswith("https://"):
        k = k[8:]
    elif k.startswith("http://"):
        k = k[7:]
    if k.startswith("www."):
        k = k[4:]
    for sep in ("?", "#"):
        idx = k.find(sep)
        if idx != -1:
            k = k[:idx]
    if k.endswith("/"):
        k = k[:-1]
    return k


@bp.route("/journalists/<int:jid>/articles", methods=["GET"])
@require_auth
def get_articles(jid):
    j = query("SELECT id FROM journalists WHERE id=?", (jid,), one=True)
    if not j:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404
    rows = query(
        "SELECT * FROM articles WHERE journalist_id=? ORDER BY date DESC, scraped_at DESC",
        (jid,)
    )
    for r in rows:
        if r.get("topics_inferred"):
            try:
                r["topics_inferred"] = json.loads(r["topics_inferred"])
            except (ValueError, TypeError):
                r["topics_inferred"] = []
    return jsonify({"articles": rows})


@bp.route("/journalists/<int:jid>/articles", methods=["POST"])
@require_auth
def add_articles(jid):
    j = query("SELECT id FROM journalists WHERE id=?", (jid,), one=True)
    if not j:
        return jsonify({"error": "not_found", "message": "journalist not found"}), 404

    data = request.get_json(silent=True) or {}
    articles = data.get("articles") or []
    if not isinstance(articles, list):
        return jsonify({"error": "validation", "message": "articles must be array"}), 400

    created = 0
    skipped = 0
    ts = now()

    for art in articles:
        title = (art.get("title") or "").strip()
        url = (art.get("url") or "").strip()
        if not title or not url:
            continue
        canon = _canonical_url(url)
        topics = art.get("topics_inferred") or art.get("topics") or []
        topics_json = json.dumps(topics) if topics else None
        existing = query(
            "SELECT id FROM articles WHERE url=? OR (url_canonical IS NOT NULL AND url_canonical=?)",
            (url, canon), one=True,
        )
        if existing:
            skipped += 1
            continue
        try:
            execute(
                "INSERT INTO articles (journalist_id, title, url, url_canonical, date, topics_inferred, scraped_at) VALUES (?,?,?,?,?,?,?)",
                (jid, title, url, canon or None, (art.get("date") or "").strip() or None, topics_json, ts)
            )
            created += 1
        except sqlite3.IntegrityError:
            skipped += 1

    return jsonify({"created": created, "skipped_dupe": skipped})


@bp.route("/articles/dedup", methods=["POST"])
@require_admin
def dedup_articles():
    """Merge articles with same canonical URL. Admin only.

    Query params:
      dry_run=1 (default) — return preview, no deletions
      dry_run=0 — execute delete + audit each victim

    Winner per group: lowest id (earliest insert). Others = victims.
    """
    user = get_user()
    role = get_role(user)
    dry_run = request.args.get("dry_run", "1") != "0"

    rows = query("SELECT id, journalist_id, title, url FROM articles ORDER BY id")

    groups = {}
    for r in rows:
        canon = _canonical_url(r.get("url") or "")
        if not canon:
            continue
        groups.setdefault(canon, []).append(r)

    dupe_groups = {k: v for k, v in groups.items() if len(v) > 1}

    victims = []
    for canon, arts in dupe_groups.items():
        winner = arts[0]
        for loser in arts[1:]:
            victims.append({
                "id": loser["id"],
                "journalist_id": loser["journalist_id"],
                "title": loser["title"],
                "url": loser["url"],
                "canon": canon,
                "winner_id": winner["id"],
            })

    summary = {
        "dry_run": dry_run,
        "total_articles": len(rows),
        "dupe_groups": len(dupe_groups),
        "victims": len(victims),
        "sample_victims": victims[:20],
    }

    if dry_run:
        return jsonify(summary)

    deleted = 0
    ts = now()
    for v in victims:
        execute("DELETE FROM articles WHERE id=?", (v["id"],))
        execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, field, old_value, new_value, user, role, ts) VALUES ('article',?,?,?,?,?,?,?,?)",
            (v["id"], "delete", "url", v["url"], f"merged_into:{v['winner_id']}", user, role, ts),
        )
        deleted += 1

    summary["deleted"] = deleted
    return jsonify(summary)
