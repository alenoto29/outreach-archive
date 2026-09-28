"""The checked-in fictional CSV follows the same browser import path as user files."""
import csv
import io
from pathlib import Path


HEADERS = {"Authorization": "Bearer testtoken"}
SAMPLE = Path(__file__).resolve().parents[2] / "examples" / "journalists-demo.csv"


def upload(client, content, dry_run=False):
    return client.post(
        "/api/import/csv" + ("?dry_run=1" if dry_run else ""),
        data={"file": (io.BytesIO(content), "contacts.csv")},
        content_type="multipart/form-data", headers=HEADERS,
    )


def test_sample_csv_preview_import_and_repeat(client):
    body = SAMPLE.read_bytes()
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8"))))
    assert len(rows) == 12
    assert all(r["email"].endswith(".example") and r["notes"] == "Synthetic demo contact" for r in rows), [(r["email"], r["notes"]) for r in rows if r["notes"] != "Synthetic demo contact"]

    before = client.get("/api/export/json", headers=HEADERS).get_json()["_meta"]["total_journalists"]
    preview = upload(client, body, dry_run=True)
    assert preview.status_code == 200
    assert preview.get_json()["created"] == 12
    assert preview.get_json()["errors"] == []
    assert client.get("/api/export/json", headers=HEADERS).get_json()["_meta"]["total_journalists"] == before

    result = upload(client, body)
    assert result.get_json()["created"] == 12
    exported = client.get("/api/export/json", headers=HEADERS).get_json()
    assert exported["_meta"]["total_journalists"] == before + 12
    demo_rows = [j for j in exported["journalists"] if j["email"].endswith(".example")]
    assert sum(bool(j["first_name"] and j["last_name"] and j["publisher"] and j["topics"] and j["email_status"]) for j in demo_rows) == 10
    sample = next(j for j in exported["journalists"] if j["email"] == "elena.vale@cronacaverde.example")
    assert sample["dr"] == 76
    assert sample["topics"] == ["Energy"]
    assert sample["reports_count"] == 1
    assert sample["contact_count"] == 2
    assert upload(client, body, dry_run=True).get_json()["updated"] == 12


def test_invalid_rows_preview_does_not_write_and_update_preserves_missing_fields(client):
    body = ("email,market,first_name,publisher,dr\n"
            "importcase@example.test,IT,Fable,Example News,54\n"
            "broken,IT,No,Example News,50\n"
            "importcase@example.test,IT,Duplicate,Example News,54\n").encode()
    preview = upload(client, body, dry_run=True).get_json()
    assert (preview["created"], preview["skipped"], len(preview["errors"])) == (1, 1, 2)
    assert upload(client, body).get_json()["created"] == 1
    update = upload(client, b"email,market,first_name\nimportcase@example.test,IT,Updated\n")
    assert update.get_json()["updated"] == 1
    j = client.get("/api/export/json", headers=HEADERS).get_json()["journalists"]
    record = next(r for r in j if r["email"] == "importcase@example.test")
    assert record["publisher"] == "Example News" and record["first_name"] == "Updated"
    assert record["dr"] == 54


def test_import_rejects_unknown_columns_and_bad_counts(client):
    r = upload(client, b"email,market,secret\nx@example.test,IT,private\n", dry_run=True)
    assert r.status_code == 400 and "secret" in r.get_json()["message"]
    result = upload(client, b"email,market,contact_count\nx@example.test,IT,-1\n", dry_run=True)
    assert result.get_json()["errors"][0]["row"] == 2


def test_large_csv_preview_has_correct_count(client):
    body = "email,market\n" + "".join(f"load{i}@example.test,IT\n" for i in range(2000))
    result = upload(client, body.encode(), dry_run=True).get_json()
    assert result["created"] == 2000 and result["errors"] == []


def test_sample_download_is_allowlisted_only(client):
    assert client.get("/examples/journalists-demo.csv").status_code == 200
    assert client.get("/csv-import.js").status_code == 200
    assert client.get("/data.json").status_code == 404


def test_editor_cannot_import(client):
    response = client.post("/api/import/csv", data={"file": (io.BytesIO(SAMPLE.read_bytes()), "demo.csv")},
                           content_type="multipart/form-data", headers={"Authorization": "Bearer editortoken"})
    assert response.status_code == 403
