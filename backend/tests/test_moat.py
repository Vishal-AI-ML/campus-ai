"""Verified-data moat: an unverified (pending) skill must NOT count as verified.

This is the core product guarantee - only mentor-verified data should flow into
resume/eligibility/recruiter surfaces. We assert a pending claim is invisible to
a verified-only read, and only appears after the mentor verifies it.
"""

import models


def test_unverified_skill_does_not_count_as_verified(client, make_user, token_header):
    student = make_user("moatstu@test.dev", role=models.UserRole.student)
    make_user("moatteach@test.dev", role=models.UserRole.teacher)

    stu_headers = token_header("moatstu@test.dev")
    teach_headers = token_header("moatteach@test.dev")

    # Student claims a skill -> starts pending.
    claim = client.post(
        "/skills",
        json={"name": "FastAPI", "evidence_url": "https://github.com/me/proj"},
        headers=stu_headers,
    )
    assert claim.status_code == 201, claim.text
    skill_id = claim.json()["id"]
    assert claim.json()["status"] == "pending"

    # Moat guard: a pending claim must NOT surface in a verified-only read.
    before = client.get(
        f"/skills/student/{student.id}?status_filter=verified", headers=teach_headers
    )
    assert before.status_code == 200
    assert before.json() == []

    # Mentor verifies the claim.
    decision = client.patch(
        f"/skills/{skill_id}/decision",
        json={"status": "verified"},
        headers=teach_headers,
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "verified"

    # Now (and only now) it counts as verified.
    after = client.get(
        f"/skills/student/{student.id}?status_filter=verified", headers=teach_headers
    )
    assert after.status_code == 200
    assert [s["name"] for s in after.json()] == ["FastAPI"]
