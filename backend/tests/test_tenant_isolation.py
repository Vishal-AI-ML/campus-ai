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


def test_internship_queue_and_reads_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    iit = make_tenant(slug="iit-i", name="IIT Internships")
    nit = make_tenant(slug="nit-i", name="NIT Internships")

    make_user("iiti.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("iiti.tpo@test.dev", role=models.UserRole.tpo, tenant=iit)
    nit_stu = make_user("niti.stu@test.dev", role=models.UserRole.student, tenant=nit)

    # Each student logs an internship inside their own institute.
    assert (
        client.post(
            "/internships",
            json={"organization": "Acme", "role_title": "SWE Intern"},
            headers=token_header("iiti.stu@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/internships",
            json={"organization": "Globex", "role_title": "Data Intern"},
            headers=token_header("niti.stu@test.dev"),
        ).status_code
        == 201
    )

    # The IIT TPO's queue shows ONLY the IIT claim.
    queue = client.get(
        "/internships/queue", headers=token_header("iiti.tpo@test.dev")
    )
    assert queue.status_code == 200
    assert [i["organization"] for i in queue.json()] == ["Acme"]

    # The IIT TPO cannot read an NIT student's internships -> empty.
    cross = client.get(
        f"/internships/student/{nit_stu.id}",
        headers=token_header("iiti.tpo@test.dev"),
    )
    assert cross.status_code == 200
    assert cross.json() == []
