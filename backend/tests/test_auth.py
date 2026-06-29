"""Auth: registration always makes a student, login issues a JWT, /me works."""


def test_register_creates_student(client, make_tenant):
    make_tenant(slug="acme")
    resp = client.post(
        "/auth/register",
        json={
            "email": "s1@test.dev",
            "full_name": "Stu One",
            "password": "secret123",
            "tenant_slug": "acme",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "s1@test.dev"
    assert body["role"] == "student"
    assert body["is_active"] is True


def test_register_ignores_role_escalation(client, make_tenant):
    """SECURITY: a caller cannot self-promote; the schema drops any role field."""
    make_tenant(slug="acme")
    resp = client.post(
        "/auth/register",
        json={
            "email": "sneaky@test.dev",
            "full_name": "Sneaky",
            "password": "secret123",
            "role": "admin",
            "tenant_slug": "acme",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "student"


def test_register_duplicate_email_conflicts(client, make_tenant):
    make_tenant(slug="acme")
    payload = {
        "email": "dup@test.dev",
        "full_name": "Dup",
        "password": "secret123",
        "tenant_slug": "acme",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_register_unknown_institute_is_404(client):
    """SECURITY: signing up into a non-existent institute is rejected (no orphan users)."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "ghost@test.dev",
            "full_name": "Ghost",
            "password": "secret123",
            "tenant_slug": "does-not-exist",
        },
    )
    assert resp.status_code == 404, resp.text


def test_login_and_me(client, make_user, token_header):
    make_user("login@test.dev")
    resp = client.get("/auth/me", headers=token_header("login@test.dev"))
    assert resp.status_code == 200
    assert resp.json()["email"] == "login@test.dev"


def test_login_wrong_password_is_401(client, make_user):
    make_user("wrong@test.dev")
    resp = client.post(
        "/auth/login", data={"username": "wrong@test.dev", "password": "nope"}
    )
    assert resp.status_code == 401
