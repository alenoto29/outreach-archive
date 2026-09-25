"""
Fuzz tests. Run from backend/: python3 -m pytest tests/test_fuzz.py -v
"""
import pytest

TOKEN = "testtoken"
HEADERS_ADMIN = {"Authorization": "Bearer testtoken", "X-User-Name": "admin_user"}

FUZZ_INJECTION = [
    "'; DROP TABLE journalists; --",
    '{"$ne": null}',
    "../../etc/passwd",
    "\x00\x01\x02",
    "<script>alert(1)</script>",
    "a" * 10_000,
]


def _post_j(fuzz_client, data):
    return fuzz_client.post("/api/journalists", json=data, headers=HEADERS_ADMIN)


def _post_p(fuzz_client, data):
    return fuzz_client.post("/api/publishers", json=data, headers=HEADERS_ADMIN)


class TestJournalistFuzz:
    def test_empty_payload(self, fuzz_client):
        r = _post_j(fuzz_client, {})
        assert r.status_code == 400

    def test_no_email(self, fuzz_client):
        r = _post_j(fuzz_client, {"market": "IT"})
        assert r.status_code == 400
        assert r.get_json()["field"] == "email"

    def test_invalid_emails(self, fuzz_client):
        # "nodot@localhost" has @ and neither starts/ends with @ — passes validation (RFC-valid)
        bad_emails = ["", "   ", "notanemail", "@nodomain", "no@"]
        for email in bad_emails:
            r = _post_j(fuzz_client, {"email": email, "market": "IT"})
            assert r.status_code == 400, f"should reject: {email!r}"

    def test_invalid_markets(self, fuzz_client):
        # "ES " normalizes to "ES" (valid) — not in this list
        for market in ["", "ZZ", "it", "FRA", "null"]:
            r = _post_j(fuzz_client, {"email": f"mktfuzz_{market}@example.test", "market": market})
            assert r.status_code == 400, f"should reject market: {market!r}"

    def test_sql_injection_email(self, fuzz_client):
        for s in FUZZ_INJECTION:
            r = _post_j(fuzz_client, {"email": f"{s}@example.test", "market": "IT"})
            assert r.status_code != 500, f"500 on injection: {s!r}"

    def test_long_field(self, fuzz_client):
        r = _post_j(fuzz_client, {
            "email": "longfield@example.test",
            "market": "IT",
            "first_name": "a" * 100_000,
        })
        assert r.status_code in (201, 409)

    def test_wrong_types(self, fuzz_client):
        r = _post_j(fuzz_client, {"email": 12345, "market": "IT"})
        assert r.status_code in (400, 201, 409)

        r = _post_j(fuzz_client, {"email": ["array"], "market": "IT"})
        assert r.status_code in (400, 201, 409)

    def test_extra_fields_ignored(self, fuzz_client):
        r = _post_j(fuzz_client, {
            "email": "extra_fuzz@example.test",
            "market": "IT",
            "evil": "payload",
            "deleted_at": "2000-01-01",
            "id": 999999,
        })
        assert r.status_code in (201, 409)
        if r.status_code == 201:
            d = r.get_json()
            assert d.get("id") != 999999

    def test_null_body(self, fuzz_client):
        r = fuzz_client.post(
            "/api/journalists",
            data="null",
            content_type="application/json",
            headers=HEADERS_ADMIN,
        )
        assert r.status_code == 400


class TestPublisherFuzz:
    def test_missing_name(self, fuzz_client):
        r = _post_p(fuzz_client, {"market": "IT"})
        assert r.status_code == 400

    def test_invalid_market(self, fuzz_client):
        r = _post_p(fuzz_client, {"name": "FuzzPub", "market": "INVALID"})
        assert r.status_code == 400

    def test_sql_injection_name(self, fuzz_client):
        for s in FUZZ_INJECTION:
            r = _post_p(fuzz_client, {"name": s, "market": "IT"})
            assert r.status_code != 500, f"500 on injection name: {s!r}"

    def test_dr_boundary(self, fuzz_client):
        for dr in [0, 100]:
            r = _post_p(fuzz_client, {"name": f"DrBound{dr}", "market": "ES", "dr": dr})
            assert r.status_code in (201, 409)

    def test_dr_string_abc(self, fuzz_client):
        r = _post_p(fuzz_client, {"name": "DrString", "market": "ES", "dr": "abc"})
        assert r.status_code in (201, 409)  # dr stored as None


class TestSearchFuzz:
    def test_sql_injection_search(self, fuzz_client):
        for s in FUZZ_INJECTION:
            r = fuzz_client.get(
                f"/api/journalists?search={s}",
                headers=HEADERS_ADMIN,
            )
            assert r.status_code not in (500,), f"search injection: {s!r}"

    def test_empty_search(self, fuzz_client):
        r = fuzz_client.get("/api/journalists?search=", headers=HEADERS_ADMIN)
        assert r.status_code == 200

    def test_limit_clamped(self, fuzz_client):
        r = fuzz_client.get("/api/journalists?limit=99999", headers=HEADERS_ADMIN)
        assert r.status_code == 200
        assert len(r.get_json()["journalists"]) <= 1000

    def test_negative_offset(self, fuzz_client):
        r = fuzz_client.get("/api/journalists?offset=-1", headers=HEADERS_ADMIN)
        assert r.status_code in (200, 400)

    def test_unicode_search(self, fuzz_client):
        r = fuzz_client.get("/api/journalists?search=Ñoño", headers=HEADERS_ADMIN)
        assert r.status_code == 200
