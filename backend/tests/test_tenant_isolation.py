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


def test_project_queue_is_tenant_scoped_and_blocks_outside_teammates(
    client, make_user, make_tenant, token_header
):
    iit = make_tenant(slug="iit-p", name="IIT Projects")
    nit = make_tenant(slug="nit-p", name="NIT Projects")

    make_user("iitp.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("iitp.teach@test.dev", role=models.UserRole.teacher, tenant=iit)
    nit_stu = make_user("nitp.stu@test.dev", role=models.UserRole.student, tenant=nit)

    # Each student creates a solo project in their own institute (owner is added
    # as a pending member automatically).
    assert (
        client.post(
            "/projects",
            json={"title": "Campus AI", "is_group": False},
            headers=token_header("iitp.stu@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/projects",
            json={"title": "Other Project", "is_group": False},
            headers=token_header("nitp.stu@test.dev"),
        ).status_code
        == 201
    )

    # The IIT mentor's review queue shows ONLY IIT contributions.
    queue = client.get(
        "/projects/queue", headers=token_header("iitp.teach@test.dev")
    )
    assert queue.status_code == 200
    assert {row["project_title"] for row in queue.json()} == {"Campus AI"}

    # A group project cannot pull in a teammate from another institute -> 400.
    blocked = client.post(
        "/projects",
        json={
            "title": "Cross Project",
            "is_group": True,
            "members": [{"student_id": nit_stu.id, "contribution": "ML"}],
        },
        headers=token_header("iitp.stu@test.dev"),
    )
    assert blocked.status_code == 400, blocked.text


def test_announcements_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    iit = make_tenant(slug="iit-a", name="IIT Announce")
    nit = make_tenant(slug="nit-a", name="NIT Announce")

    make_user("iita.admin@test.dev", role=models.UserRole.admin, tenant=iit)
    make_user("iita.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("nita.admin@test.dev", role=models.UserRole.admin, tenant=nit)

    # Each admin broadcasts to everyone inside their own institute.
    assert (
        client.post(
            "/announcements",
            json={"title": "IIT Fest", "body": "This Friday", "audience": "all"},
            headers=token_header("iita.admin@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/announcements",
            json={"title": "NIT Fest", "body": "Next week", "audience": "all"},
            headers=token_header("nita.admin@test.dev"),
        ).status_code
        == 201
    )

    # The IIT admin's governance view shows ONLY IIT's post (not NIT's).
    admin_list = client.get(
        "/announcements", headers=token_header("iita.admin@test.dev")
    )
    assert admin_list.status_code == 200
    assert [a["title"] for a in admin_list.json()] == ["IIT Fest"]

    # An IIT student only ever sees their own institute's "all" broadcast.
    stu_list = client.get(
        "/announcements", headers=token_header("iita.stu@test.dev")
    )
    assert stu_list.status_code == 200
    assert [a["title"] for a in stu_list.json()] == ["IIT Fest"]


def test_open_drives_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    iit = make_tenant(slug="iit-d", name="IIT Drives")
    nit = make_tenant(slug="nit-d", name="NIT Drives")

    make_user("iitd.tpo@test.dev", role=models.UserRole.tpo, tenant=iit)
    make_user("iitd.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("nitd.tpo@test.dev", role=models.UserRole.tpo, tenant=nit)

    # Each TPO posts a placement drive inside their own institute.
    assert (
        client.post(
            "/drives",
            json={"company_name": "Acme", "role_title": "Backend Engineer"},
            headers=token_header("iitd.tpo@test.dev"),
        ).status_code
        == 201
    )
    nit_drive = client.post(
        "/drives",
        json={"company_name": "Globex", "role_title": "Data Engineer"},
        headers=token_header("nitd.tpo@test.dev"),
    )
    assert nit_drive.status_code == 201
    nit_drive_id = nit_drive.json()["id"]

    # An IIT student browsing open drives sees ONLY IIT's drive.
    open_list = client.get(
        "/drives/open", headers=token_header("iitd.stu@test.dev")
    )
    assert open_list.status_code == 200
    assert [d["company_name"] for d in open_list.json()] == ["Acme"]

    # The IIT TPO cannot open NIT's drive by id -> hidden as 404.
    cross = client.get(
        f"/drives/{nit_drive_id}", headers=token_header("iitd.tpo@test.dev")
    )
    assert cross.status_code == 404, cross.text
