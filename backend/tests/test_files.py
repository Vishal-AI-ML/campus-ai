"""Tests for the /files signing routes (Section 7, Part B).

Supabase is never reached: when the feature is OFF the routes must 503, and
when ON we stub the two network helpers so we can assert auth, validation and
tenant-isolation behaviour deterministically/offline.
"""

import storage
from models import UserRole


def _enable_storage(monkeypatch):
    """Pretend Supabase is configured and stub the two network calls."""
    monkeypatch.setattr(storage, "storage_enabled", lambda: True)
    monkeypatch.setattr(
        storage,
        "create_signed_upload_url",
        lambda path: {
            "path": path,
            "upload_url": f"https://x.supabase.co/storage/v1/object/upload/sign/b/{path}?token=t",
            "token": "t",
        },
    )
    monkeypatch.setattr(
        storage,
        "create_signed_download_url",
        lambda path, expires_in=600: f"https://x.supabase.co/storage/v1/object/sign/b/{path}?token=t",
    )


# --- Feature OFF (default test env has no SUPABASE_* set) --------------------


def test_sign_upload_disabled_returns_503(client, make_user, token_header):
    make_user("s1@x.edu", role=UserRole.student)
    headers = token_header("s1@x.edu")
    resp = client.post(
        "/files/sign-upload",
        json={"filename": "cert.pdf", "kind": "certificate"},
        headers=headers,
    )
    assert resp.status_code == 503, resp.text


def test_sign_upload_requires_auth(client):
    resp = client.post(
        "/files/sign-upload", json={"filename": "cert.pdf", "kind": "certificate"}
    )
    assert resp.status_code == 401


# --- Feature ON (stubbed) ---------------------------------------------------


def test_sign_upload_ok_path_is_tenant_scoped(
    client, make_user, token_header, monkeypatch
):
    _enable_storage(monkeypatch)
    user = make_user("s2@x.edu", role=UserRole.student)
    headers = token_header("s2@x.edu")
    resp = client.post(
        "/files/sign-upload",
        json={"filename": "my proof!.PDF", "kind": "certificate"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Path must start with the caller's tenant + kind + user id.
    assert body["path"].startswith(f"{user.tenant_id}/certificate/{user.id}/")
    # Filename is sanitised (space/! gone) and extension lower-cased.
    assert body["path"].endswith(".pdf")
    assert " " not in body["path"] and "!" not in body["path"]
    assert body["upload_url"].startswith("https://")


def test_sign_upload_rejects_bad_extension(
    client, make_user, token_header, monkeypatch
):
    _enable_storage(monkeypatch)
    make_user("s3@x.edu", role=UserRole.student)
    headers = token_header("s3@x.edu")
    resp = client.post(
        "/files/sign-upload",
        json={"filename": "virus.exe", "kind": "certificate"},
        headers=headers,
    )
    assert resp.status_code == 415, resp.text


def test_sign_upload_rejects_unknown_kind(
    client, make_user, token_header, monkeypatch
):
    _enable_storage(monkeypatch)
    make_user("s4@x.edu", role=UserRole.student)
    headers = token_header("s4@x.edu")
    resp = client.post(
        "/files/sign-upload",
        json={"filename": "a.pdf", "kind": "nope"},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text


def test_sign_download_own_tenant_ok(client, make_user, token_header, monkeypatch):
    _enable_storage(monkeypatch)
    user = make_user("s5@x.edu", role=UserRole.student)
    headers = token_header("s5@x.edu")
    path = f"{user.tenant_id}/certificate/{user.id}/abc-cert.pdf"
    resp = client.post(
        "/files/sign-download", json={"path": path}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["download_url"].startswith("https://")


def test_sign_download_other_tenant_forbidden(
    client, make_user, token_header, monkeypatch
):
    _enable_storage(monkeypatch)
    user = make_user("s6@x.edu", role=UserRole.student)
    headers = token_header("s6@x.edu")
    other = user.tenant_id + 999
    resp = client.post(
        "/files/sign-download",
        json={"path": f"{other}/certificate/1/x.pdf"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


def test_sign_download_blocks_path_traversal(
    client, make_user, token_header, monkeypatch
):
    _enable_storage(monkeypatch)
    user = make_user("s7@x.edu", role=UserRole.student)
    headers = token_header("s7@x.edu")
    resp = client.post(
        "/files/sign-download",
        json={"path": f"{user.tenant_id}/../{user.tenant_id + 1}/x.pdf"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text
