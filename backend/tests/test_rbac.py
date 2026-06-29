"""RBAC: role-gated routes reject the wrong role (403) and missing tokens (401)."""

import models


def test_no_token_is_401(client):
    assert client.get("/auth/me").status_code == 401


def test_student_cannot_access_mentor_queue(client, make_user, token_header):
    make_user("rbacstu@test.dev", role=models.UserRole.student)
    resp = client.get("/skills/queue", headers=token_header("rbacstu@test.dev"))
    assert resp.status_code == 403


def test_teacher_can_access_mentor_queue(client, make_user, token_header):
    make_user("rbacteach@test.dev", role=models.UserRole.teacher)
    resp = client.get("/skills/queue", headers=token_header("rbacteach@test.dev"))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_inactive_user_token_rejected(client, make_user, token_header, session):
    user = make_user("inactive@test.dev")
    headers = token_header("inactive@test.dev")  # minted while still active
    user.is_active = False
    session.commit()
    assert client.get("/auth/me", headers=headers).status_code == 401
