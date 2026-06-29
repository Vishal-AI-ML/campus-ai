"""Tenant isolation (Phase 3): one institute can never see another's skill data.

This is the payoff of giving `skills` a `tenant_id` and filtering every query by
it. Two institutes (IIT, NIT) each have a student + a teacher; we assert an IIT
mentor sees only IIT claims and cannot read an NIT student's skills.
"""

import models


def test_skill_queue_and_reads_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    iit = make_tenant(slug="iit", name="IIT")
    nit = make_tenant(slug="nit", name="NIT")

    make_user("iit.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("iit.teach@test.dev", role=models.UserRole.teacher, tenant=iit)
    nit_stu = make_user("nit.stu@test.dev", role=models.UserRole.student, tenant=nit)
    make_user("nit.teach@test.dev", role=models.UserRole.teacher, tenant=nit)

    # Each student claims a skill inside their own institute.
    assert (
        client.post(
            "/skills",
            json={"name": "FastAPI"},
            headers=token_header("iit.stu@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/skills",
            json={"name": "Django"},
            headers=token_header("nit.stu@test.dev"),
        ).status_code
        == 201
    )

    # The IIT mentor's verification queue shows ONLY the IIT claim.
    queue = client.get(
        "/skills/queue", headers=token_header("iit.teach@test.dev")
    )
    assert queue.status_code == 200
    assert [s["name"] for s in queue.json()] == ["FastAPI"]

    # The IIT mentor cannot read an NIT student's skills -> tenant-scoped empty.
    cross = client.get(
        f"/skills/student/{nit_stu.id}",
        headers=token_header("iit.teach@test.dev"),
    )
    assert cross.status_code == 200
    assert cross.json() == []
