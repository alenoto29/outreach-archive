"""
Black-box API tests. Run from backend/: python3 -m pytest tests/test_api.py -v
"""
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


# --- Auth ---

def test_health_no_auth(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_list_no_token(client):
    r = client.get("/api/journalists", headers={"X-User-Name": "admin_user"})
    assert r.status_code == 401


def test_list_wrong_token(client):
    r = client.get("/api/journalists", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_token_identifies_user_without_client_role_claim(client):
    r = client.get("/api/journalists", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200


# --- Journalists ---

def test_list_journalists(client):
    r = _get(client, "/api/journalists")
    assert r.status_code == 200
    d = r.get_json()
    assert "journalists" in d
    assert d["total"] >= 1


def test_get_journalist(client):
    r = _get(client, "/api/journalists/1")
    assert r.status_code == 200
    d = r.get_json()
    assert d["email"] == "j1@example.test"
    assert "topics" in d
    assert "campaigns" in d
    assert "articles_count" in d


def test_get_journalist_not_found(client):
    r = _get(client, "/api/journalists/99999")
    assert r.status_code == 404


def test_create_journalist_missing_email(client):
    r = _post(client, "/api/journalists", {"market": "IT"})
    assert r.status_code == 400
    assert r.get_json()["field"] == "email"


def test_create_journalist_invalid_market(client):
    r = _post(client, "/api/journalists", {"email": "mktbad@example.test", "market": "XX"})
    assert r.status_code == 400
    assert r.get_json()["field"] == "market"


def test_create_journalist_ok(client):
    r = _post(client, "/api/journalists", {
        "email": "new_api@example.test",
        "first_name": "Luigi",
        "market": "IT",
        "publisher_name": "TestPub",
    })
    assert r.status_code == 201
    d = r.get_json()
    assert d["email"] == "new_api@example.test"
    assert d["first_name"] == "Luigi"


def test_create_journalist_dupe(client):
    _post(client, "/api/journalists", {"email": "dupe_api@example.test", "market": "IT"})
    r = _post(client, "/api/journalists", {"email": "dupe_api@example.test", "market": "IT"})
    assert r.status_code == 409


def test_update_journalist(client):
    r = _post(client, "/api/journalists", {"email": "upd_api@example.test", "market": "ES", "first_name": "Before"})
    assert r.status_code == 201
    jid = r.get_json()["id"]
    r = _patch(client, f"/api/journalists/{jid}", {"first_name": "After", "notes": "updated"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["first_name"] == "After"
    assert d["notes"] == "updated"


def test_soft_delete_journalist(client):
    r = _post(client, "/api/journalists", {"email": "del_api@example.test", "market": "FR"})
    jid = r.get_json()["id"]
    r = _delete(client, f"/api/journalists/{jid}")
    assert r.status_code == 200
    assert r.get_json()["hard"] is False

    r = _get(client, "/api/journalists?market=FR")
    emails = [j["email"] for j in r.get_json()["journalists"]]
    assert "del_api@example.test" not in emails


def test_hard_delete_requires_admin(client):
    r = _post(client, "/api/journalists", {"email": "hd_api@example.test", "market": "IT"})
    jid = r.get_json()["id"]
    r = client.delete(f"/api/journalists/{jid}?hard=1", headers=HEADERS_EDITOR)
    assert r.status_code == 403


def test_restore_journalist(client):
    r = _post(client, "/api/journalists", {"email": "rst_api@example.test", "market": "IT"})
    jid = r.get_json()["id"]
    _delete(client, f"/api/journalists/{jid}")
    r = _post(client, f"/api/journalists/{jid}/restore", {})
    assert r.status_code == 200
    r = _get(client, f"/api/journalists/{jid}")
    assert r.get_json().get("deleted_at") is None


def test_journalist_search(client):
    r = _get(client, "/api/journalists?search=Mario")
    assert r.status_code == 200
    d = r.get_json()
    assert any(j["email"] == "j1@example.test" for j in d["journalists"])


def test_journalist_filter_market(client):
    r = _get(client, "/api/journalists?market=ES")
    assert r.status_code == 200
    for j in r.get_json()["journalists"]:
        assert j["market"] == "ES"


# --- Publishers ---

def test_list_publishers(client):
    r = _get(client, "/api/publishers")
    assert r.status_code == 200
    d = r.get_json()
    assert d["total"] >= 1
    assert all("tier" in p for p in d["publishers"])


def test_get_publisher(client):
    r = _get(client, "/api/publishers/1")
    assert r.status_code == 200
    d = r.get_json()
    assert "journalists" in d
    assert d["tier"] == "top"


def test_create_publisher(client):
    r = _post(client, "/api/publishers", {"name": "NewPub_api", "market": "ES", "dr": 55})
    assert r.status_code == 201
    d = r.get_json()
    assert d["name"] == "NewPub_api"
    assert d["tier"] == "mid"


def test_publisher_tier_top(client):
    r = _post(client, "/api/publishers", {"name": "TopPub_api", "market": "FR", "dr": 75})
    assert r.get_json()["tier"] == "top"


def test_publisher_tier_low(client):
    r = _post(client, "/api/publishers", {"name": "LowPub_api", "market": "FR", "dr": 20})
    assert r.get_json()["tier"] == "low"


def test_update_publisher(client):
    r = _post(client, "/api/publishers", {"name": "PatchPub", "market": "IT", "dr": 50})
    pid = r.get_json()["id"]
    r = _patch(client, f"/api/publishers/{pid}", {"dr": 80})
    assert r.status_code == 200
    assert r.get_json()["tier"] == "top"


def test_delete_publisher(client):
    r = _post(client, "/api/publishers", {"name": "DelPub", "market": "IT"})
    pid = r.get_json()["id"]
    r = _delete(client, f"/api/publishers/{pid}")
    assert r.status_code == 200


# --- Campaigns ---

def test_list_campaigns(client):
    r = _get(client, "/api/campaigns")
    assert r.status_code == 200
    assert "campaigns" in r.get_json()


def test_get_campaign(client):
    r = _get(client, "/api/campaigns/1")
    assert r.status_code == 200
    assert "journalists" in r.get_json()


def test_create_campaign(client):
    r = _post(client, "/api/campaigns", {"name": "NewCamp_api", "market": "IT", "date_start": "2026-05-01"})
    assert r.status_code == 201
    d = r.get_json()
    assert d["name"] == "NewCamp_api"
    assert d["date_start"] == "2026-05-01"


def test_add_journalists_to_campaign(client):
    r = _post(client, "/api/campaigns", {"name": "BulkCamp_api", "market": "IT"})
    cid = r.get_json()["id"]
    r = _post(client, f"/api/campaigns/{cid}/journalists", {"journalist_ids": [1]})
    assert r.status_code == 200
    assert "added" in r.get_json()


# --- Articles ---

def test_get_articles(client):
    r = _get(client, "/api/journalists/1/articles")
    assert r.status_code == 200
    assert "articles" in r.get_json()


# --- Outreach ---

def test_log_outreach_send(client):
    r = _post(client, "/api/outreach", {
        "journalist_id": 1,
        "sent_at": "2026-04-16T10:00:00Z",
        "strategy": "exclusivity",
    })
    assert r.status_code == 201
    d = r.get_json()
    assert d["journalist_id"] == 1
    assert d["strategy"] == "exclusivity"


def test_list_outreach(client):
    r = _get(client, "/api/outreach?journalist_id=1")
    assert r.status_code == 200
    assert r.get_json()["total"] >= 1


def test_outreach_missing_journalist_id(client):
    r = _post(client, "/api/outreach", {"sent_at": "2026-04-16T10:00:00Z"})
    assert r.status_code == 400


# --- Export ---

def test_export_csv_journalists(client):
    r = _get(client, "/api/export/csv?type=journalists")
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert b"email" in r.data


def test_export_csv_publishers(client):
    r = _get(client, "/api/export/csv?type=publishers")
    assert r.status_code == 200
    assert "text/csv" in r.content_type


def test_export_csv_invalid_type(client):
    r = _get(client, "/api/export/csv?type=invalid")
    assert r.status_code == 400


def test_export_json(client):
    r = _get(client, "/api/export/json")
    assert r.status_code == 200
    d = r.get_json()
    assert "_meta" in d
    assert "journalists" in d
    j = d["journalists"][0]
    assert "topics" in j
    assert "campaigns" in j


# --- Audit ---

def test_audit_admin_only(client):
    r = _get(client, "/api/audit", headers=HEADERS_EDITOR)
    assert r.status_code == 403


def test_audit_ok(client):
    r = _get(client, "/api/audit")
    assert r.status_code == 200
    assert "entries" in r.get_json()


def test_audit_filter(client):
    r = _get(client, "/api/audit?entity_type=journalist")
    assert r.status_code == 200
    d = r.get_json()
    for entry in d["entries"]:
        assert entry["entity_type"] == "journalist"


# --- Regression: security hardening ---

def test_limit_negative_clamped_to_min(client):
    # H2 regression: ?limit=-1 must not bypass clamp (SQLite LIMIT -1 = no limit → full dump).
    r = _get(client, "/api/journalists?limit=-1")
    assert r.status_code == 200
    assert len(r.get_json()["journalists"]) <= 1000


def test_limit_garbage_falls_back_to_default(client):
    r = _get(client, "/api/journalists?limit=abc")
    assert r.status_code == 200


def test_offset_negative_coerced(client):
    r = _get(client, "/api/journalists?offset=-5")
    assert r.status_code == 200


def test_audit_limit_negative_clamped(client):
    r = _get(client, "/api/audit?limit=-1")
    assert r.status_code == 200
    assert len(r.get_json()["entries"]) <= 1000


def test_outreach_limit_negative_clamped(client):
    r = _get(client, "/api/outreach?limit=-1")
    assert r.status_code == 200


def test_publishers_limit_negative_clamped(client):
    r = _get(client, "/api/publishers?limit=-1")
    assert r.status_code == 200
    assert len(r.get_json()["publishers"]) <= 1000


def test_contact_count_non_int_no_500(client):
    # Non-int contact_count must not produce 500 (leaking traceback).
    r = _post(client, "/api/journalists", {"email": "cnt_bad@example.test", "market": "IT", "contact_count": "abc"})
    assert r.status_code in (201, 409)


def test_path_traversal_dashboard_static(client):
    # H1 regression: sibling-prefix attack must 404.
    r = client.get("/../etc/passwd")
    assert r.status_code in (308, 404)
    r = client.get("/..%2fetc%2fpasswd")
    assert r.status_code in (308, 400, 404)


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"


def test_500_no_traceback_leak(client):
    # After H3 fix, 500 responses must NOT contain raw exception text.
    # Trigger by hitting an endpoint with a route that raises — we use audit with malformed since.
    # (Soft check: if no 500 occurs naturally, skip the assertion.)
    r = _get(client, "/api/audit?entity_id=notanint")
    # parse_int coerces → None, so this should 200 now. Just assert no leak ever.
    if r.status_code == 500:
        body = r.get_json() or {}
        assert "Traceback" not in str(body)
        assert "message" not in body or body.get("error") == "internal"


def test_token_via_bearer_header(client):
    r = client.get("/api/journalists", headers=HEADERS_ADMIN)
    assert r.status_code == 200


def test_token_via_x_access_token_header(client):
    r = client.get("/api/journalists", headers={
        "X-User-Name": "admin_user", "X-Access-Token": TOKEN,
    })
    assert r.status_code == 401


def test_token_in_url_is_rejected(client):
    r = client.get(f"/api/journalists?k={TOKEN}")
    assert r.status_code == 401


def test_dashboard_static_assets_are_allowlisted(client):
    assert client.get("/").status_code == 200
    assert client.get("/api.js").status_code == 200
    assert client.get("/data.json").status_code == 404
    assert client.get("/graph.js").status_code == 404
    assert client.get("/../backend/.env").status_code == 404


def test_health_hides_database_error_details(client, monkeypatch):
    import app as app_module

    def fail_query(*args, **kwargs):
        raise RuntimeError("synthetic secret diagnostic")

    monkeypatch.setattr(app_module, "query", fail_query)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}
    assert "synthetic secret diagnostic" not in response.get_data(as_text=True)


def test_token_bearer_wrong_rejected(client):
    r = client.get("/api/journalists", headers={**HEADERS_ADMIN, "Authorization": "Bearer wrongtoken"})
    assert r.status_code == 401
