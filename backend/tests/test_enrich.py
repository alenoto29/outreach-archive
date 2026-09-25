"""Offline tests for candidate import, duplicate handling and idempotence."""
import pytest

HEADERS_ADMIN = {"Authorization": "Bearer testtoken", "X-User-Name": "admin_user"}


def _post(client, data):
    return client.post("/api/journalists/enrich", json=data, headers=HEADERS_ADMIN)


def test_enrich_requires_list(client):
    response = _post(client, {"candidates": "not-a-list"})
    assert response.status_code == 400


def test_enrich_creates_and_marks_source(client):
    response = _post(client, {"candidates": [{
        "email": "new-enrich@example.test", "first_name": "Ada", "last_name": "Example",
        "market": "IT", "publisher": "Synthetic Publication", "main_topic": "energy",
    }]})
    assert response.status_code == 200
    assert response.get_json()["created"] == 1
    rows = client.get("/api/journalists?search=new-enrich", headers=HEADERS_ADMIN).get_json()["journalists"]
    assert rows[0]["enrichment_source"] == "candidate-import"


def test_enrich_skips_existing_email(client):
    response = _post(client, {"candidates": [{
        "email": "j1@example.test", "first_name": "Different", "last_name": "Person", "market": "FR",
    }]})
    assert response.status_code == 200
    assert response.get_json()["skipped"] == 1


def test_enrich_skips_existing_name(client):
    response = _post(client, {"candidates": [{
        "email": "mario.alt@example.test", "first_name": "Mario", "last_name": "Rossi", "market": "IT",
    }]})
    assert response.status_code == 200
    assert response.get_json()["skipped"] == 1


def test_enrich_is_idempotent(client):
    candidate = {"email": "idempotent@example.test", "first_name": "Sam", "last_name": "Sample", "market": "IT"}
    first = _post(client, {"candidates": [candidate]}).get_json()
    second = _post(client, {"candidates": [candidate]}).get_json()
    assert first["created"] == 1
    assert second["skipped"] == 1


def test_enrich_reports_invalid_candidate(client):
    response = _post(client, {"candidates": [{"email": "not-an-address", "market": "IT"}]})
    assert response.status_code == 200
    assert response.get_json()["errors"]
