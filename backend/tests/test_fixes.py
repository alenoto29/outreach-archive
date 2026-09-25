"""Regression tests for fixes applied on 2026-04-22."""
import io
import json
import pytest

TOKEN = "testtoken"
HEADERS_ADMIN = {"Authorization": "Bearer testtoken", "X-User-Name": "admin_user"}
HEADERS_EDITOR = {"Authorization": "Bearer editortoken", "X-User-Name": "editor_user"}


def _get(client, path, headers=None):
    headers = headers or HEADERS_ADMIN
    return client.get(path, headers=headers)


def _post(client, path, data, headers=None):
    headers = headers or HEADERS_ADMIN
    return client.post(path, json=data, headers=headers)


def _patch(client, path, data, headers=None):
    headers = headers or HEADERS_ADMIN
    return client.patch(path, json=data, headers=headers)


def _delete(client, path, headers=None):
    headers = headers or HEADERS_ADMIN
    return client.delete(path, headers=headers)


# --- CSV import: latin-1 double-read silent data loss ---

def test_csv_import_latin1_reads_rows(client):
    body = (
        "email,first_name,last_name,market,publisher\n"
        "latin1a@example.test,José,García,ES,TestPub\n"
        "latin1b@example.test,Béatrice,Côté,FR,TestPubFR\n"
    ).encode("latin-1")
    data = {"file": (io.BytesIO(body), "in.csv")}
    r = client.post(
        "/api/import/csv",
        data=data,
        content_type="multipart/form-data",
        headers=HEADERS_ADMIN,
    )
    assert r.status_code == 200
    d = r.get_json()
    assert d["created"] + d["updated"] >= 2, f"expected 2 rows processed, got {d}"


# --- CSV import: audit log written ---

def test_csv_import_writes_audit_entries(client):
    body = (
        "email,first_name,market,publisher\n"
        "audit_csv_1@example.test,Auditor,IT,TestPub\n"
    ).encode("utf-8")
    data = {"file": (io.BytesIO(body), "in.csv")}
    r = client.post(
        "/api/import/csv",
        data=data,
        content_type="multipart/form-data",
        headers=HEADERS_ADMIN,
    )
    assert r.status_code == 200

    j = _get(client, "/api/journalists?search=audit_csv_1").get_json()
    jid = j["journalists"][0]["id"]

    r = _get(client, f"/api/audit?entity_type=journalist&entity_id={jid}")
    assert r.status_code == 200
    entries = r.get_json()["entries"]
    assert any(e["action"] == "create" for e in entries), f"missing create audit for jid {jid}"


# --- expertise_tags: list must round-trip as valid JSON ---

def test_expertise_tags_array_roundtrip(client):
    r = _post(client, "/api/journalists", {"email": "tags@example.test", "market": "IT"})
    assert r.status_code == 201
    jid = r.get_json()["id"]

    r = _patch(client, f"/api/journalists/{jid}", {"expertise_tags": ["solar", "wind"]})
    assert r.status_code == 200

    r = _get(client, f"/api/journalists/{jid}")
    assert r.status_code == 200
    raw = r.get_json()["expertise_tags"]
    assert isinstance(raw, str), f"expected serialized string, got {type(raw)}"
    assert json.loads(raw) == ["solar", "wind"], f"not valid JSON: {raw!r}"


# --- get_journalist: soft-deleted hidden by default, visible with include_deleted=1 ---

def test_get_soft_deleted_journalist_returns_404(client):
    r = _post(client, "/api/journalists", {"email": "hidden@example.test", "market": "IT"})
    jid = r.get_json()["id"]
    _delete(client, f"/api/journalists/{jid}")

    r = _get(client, f"/api/journalists/{jid}")
    assert r.status_code == 404

    r = _get(client, f"/api/journalists/{jid}?include_deleted=1")
    assert r.status_code == 200
    assert r.get_json()["deleted_at"] is not None


# --- create_journalist: constraint leak must not expose raw DB error text ---

def test_create_journalist_constraint_error_not_leaked(client):
    r = _post(client, "/api/journalists", {"email": "noatsign", "market": "IT"})
    assert r.status_code == 400
    body = r.get_json()
    assert "CHECK" not in (body.get("message") or ""), f"leaked constraint text: {body}"
    assert "LIKE" not in (body.get("message") or "")


# --- _resolve_publisher: case-insensitive lookup, no duplicate created ---

def test_publisher_resolve_case_insensitive(client):
    _post(client, "/api/publishers", {"name": "CaseTest Publisher", "market": "IT", "dr": 60})
    r = _post(client, "/api/journalists", {
        "email": "case_j@example.test",
        "market": "IT",
        "publisher_name": "casetest publisher",
    })
    assert r.status_code == 201

    r = _get(client, "/api/publishers?search=CaseTest")
    pubs = r.get_json()["publishers"]
    names = [p["name"] for p in pubs]
    matches = [n for n in names if n.lower() == "casetest publisher"]
    assert len(matches) == 1, f"duplicate case-variant publishers: {matches}"


# --- USER_TOKENS mode: per-user tokens block header impersonation ---

def test_per_user_token_blocks_admin_impersonation(client, monkeypatch):
    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "USER_TOKENS", {"alice": "tok_alice", "bob": "tok_bob"})
    monkeypatch.setattr(auth_mod, "ADMIN_NAMES", {"alice"})

    r = client.delete(
        "/api/journalists/1?hard=1",
        headers={"Authorization": "Bearer tok_bob", "X-User-Name": "alice"},
    )
    assert r.status_code == 401, f"a role-claim mismatch must fail closed: {r.status_code}"


def test_per_user_token_unknown_rejected(client, monkeypatch):
    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "USER_TOKENS", {"alice": "tok_alice"})

    r = client.get(
        "/api/journalists",
        headers={"Authorization": "Bearer notatoken", "X-User-Name": "alice"},
    )
    assert r.status_code == 401


def test_auth_fails_closed_without_user_tokens(client, monkeypatch):
    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "USER_TOKENS", {})
    monkeypatch.setattr(auth_mod, "ADMIN_NAMES", {"admin_user"})
    r = client.get("/api/journalists", headers={
        "Authorization": "Bearer testtoken", "X-User-Name": "admin_user",
    })
    assert r.status_code == 401


def test_per_user_token_admin_grants_access(client, monkeypatch):
    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "USER_TOKENS", {"alice": "tok_alice"})
    monkeypatch.setattr(auth_mod, "ADMIN_NAMES", {"alice"})

    r = client.get(
        "/api/audit",
        headers={"Authorization": "Bearer tok_alice"},
    )
    assert r.status_code == 200


def test_per_user_token_editor_cannot_access_admin_endpoint(client, monkeypatch):
    import auth as auth_mod
    monkeypatch.setattr(auth_mod, "USER_TOKENS", {"bob": "tok_bob"})
    monkeypatch.setattr(auth_mod, "ADMIN_NAMES", set())

    r = client.get(
        "/api/audit",
        headers={"Authorization": "Bearer tok_bob"},
    )
    assert r.status_code == 403


# --- Meta endpoint accepts bearer token without a role header ---

def test_meta_token_only_no_user_header(client):
    r = client.get("/api/meta", headers={"Authorization": "Bearer testtoken"})
    assert r.status_code == 200
    d = r.get_json()
    assert "per_market" in d


# --- Health endpoint exposes Litestream replica status ---

def test_health_does_not_expose_database_diagnostics(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.get_json()
    assert d == {"status": "ok"}


def test_csv_export_neutralizes_spreadsheet_formulas(client):
    _post(client, "/api/journalists", {
        "email": "formula@example.test", "market": "IT", "notes": "=1+1",
    })
    response = client.get("/api/export/csv?type=journalists", headers=HEADERS_ADMIN)
    assert response.status_code == 200
    assert "'=1+1" in response.get_data(as_text=True)


def test_export_etag_changes_for_same_second_audit_mutations(client):
    import db as db_mod
    from routes.import_export import _compute_export_etag

    first = _compute_export_etag()
    db_mod.execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, user) VALUES (?,?,?,?)",
        ("journalist", 1, "update", "admin_user"),
    )
    second = _compute_export_etag()
    assert first != second


# --- Articles: canonical URL dedup across protocol/www/query variants ---

def test_article_canonical_dedup(client):
    r = _post(client, "/api/journalists/1/articles", {
        "articles": [
            {"title": "Solar pact", "url": "https://example.com/a"},
            {"title": "Solar pact (retry)", "url": "http://example.com/a"},
            {"title": "Solar pact (utm)", "url": "https://www.example.com/a/?utm=fb"},
            {"title": "Solar pact (hash)", "url": "https://example.com/a#frag"},
        ]
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d["created"] == 1, f"expected 1 created, got {d}"
    assert d["skipped_dupe"] == 3, f"expected 3 skipped, got {d}"


# --- Transaction atomicity: journalist+topics+audit must rollback together ---

def test_create_journalist_rollback_on_failure(client, monkeypatch):
    """If _sync_topics crashes, the journalist INSERT must not persist."""
    from routes import journalists as j_mod

    def boom(*args, **kwargs):
        raise RuntimeError("simulated mid-transaction crash")

    monkeypatch.setattr(j_mod, "_sync_topics", boom)

    r = _post(client, "/api/journalists", {
        "email": "tx_rollback@example.test",
        "market": "IT",
        "topics": ["fake"],
    })
    assert r.status_code >= 500

    r = _get(client, "/api/journalists?search=tx_rollback")
    assert r.status_code == 200
    assert all(j["email"] != "tx_rollback@example.test" for j in r.get_json()["journalists"])


# --- Simulated race on _resolve_publisher: IntegrityError must be absorbed ---

def test_resolve_publisher_integrity_error_absorbed(client, monkeypatch):
    """Simulate a concurrent INSERT: first call sees empty, second sees UNIQUE violation."""
    import sqlite3
    from routes import journalists as j_mod

    real_execute = j_mod.execute
    call_count = {"n": 0}

    def flaky_execute(sql, params=(), conn=None):
        if "INSERT INTO publishers" in sql and call_count["n"] == 0:
            call_count["n"] = 1
            real_execute(sql, params, conn=conn)
            raise sqlite3.IntegrityError("UNIQUE constraint failed: publishers.name, publishers.market")
        return real_execute(sql, params, conn=conn)

    monkeypatch.setattr(j_mod, "execute", flaky_execute)

    r = _post(client, "/api/journalists", {
        "email": "race_sim@example.test",
        "market": "IT",
        "publisher_name": "RaceSimPub",
    })
    assert r.status_code == 201, f"race loser must recover, not 500: {r.status_code} {r.data[:200]}"

    r = _get(client, "/api/publishers?search=RaceSimPub")
    pubs = r.get_json()["publishers"]
    assert len(pubs) == 1, f"duplicate publishers after race: {pubs}"
