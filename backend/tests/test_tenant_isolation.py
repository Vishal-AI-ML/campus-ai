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


def _make_section(session, *, tenant, code, dept_name, sec_name="A"):
    """Seed a department + section directly (the public API can't create them)."""
    dept = models.Department(tenant_id=tenant.id, name=dept_name, code=code)
    session.add(dept)
    session.commit()
    session.refresh(dept)
    section = models.Section(
        tenant_id=tenant.id, name=sec_name, year=3, department_id=dept.id
    )
    session.add(section)
    session.commit()
    session.refresh(section)
    return section


def test_section_attendance_is_tenant_scoped(
    client, make_user, make_tenant, token_header, session
):
    """A teacher can only ever read attendance from their own institute.

    Even when two institutes happen to share a section id space, the
    `/attendance/section/{id}` read is filtered by tenant, so an NIT teacher
    peeking at an IIT section gets nothing back.
    """
    iit = make_tenant(slug="iit-att", name="IIT Attendance")
    nit = make_tenant(slug="nit-att", name="NIT Attendance")

    make_user("iitat.teach@test.dev", role=models.UserRole.teacher, tenant=iit)
    iit_stu = make_user(
        "iitat.stu@test.dev", role=models.UserRole.student, tenant=iit
    )
    make_user("nitat.teach@test.dev", role=models.UserRole.teacher, tenant=nit)

    iit_section = _make_section(
        session, tenant=iit, code="IIT-CSE", dept_name="IIT CSE"
    )

    # The IIT teacher marks one of their students present.
    marked = client.post(
        "/attendance/mark",
        json={
            "section_id": iit_section.id,
            "date": "2026-06-29",
            "records": [{"student_id": iit_stu.id, "status": "present"}],
        },
        headers=token_header("iitat.teach@test.dev"),
    )
    assert marked.status_code in (200, 201), marked.text

    # The IIT teacher reading their own section sees the record.
    own = client.get(
        f"/attendance/section/{iit_section.id}",
        headers=token_header("iitat.teach@test.dev"),
    )
    assert own.status_code == 200
    assert [r["student_id"] for r in own.json()] == [iit_stu.id]

    # An NIT teacher reading the very same section id sees nothing -> isolated.
    cross = client.get(
        f"/attendance/section/{iit_section.id}",
        headers=token_header("nitat.teach@test.dev"),
    )
    assert cross.status_code == 200
    assert cross.json() == []


def test_doubts_are_tenant_scoped(
    client, make_user, make_tenant, token_header, session
):
    """The doubt forum never leaks across institutes.

    An IIT teacher posts a doubt; an NIT admin neither sees it in the
    governance list nor can open it by id (hidden as 404).
    """
    iit = make_tenant(slug="iit-dbt", name="IIT Doubts")
    nit = make_tenant(slug="nit-dbt", name="NIT Doubts")

    make_user("iitdbt.teach@test.dev", role=models.UserRole.teacher, tenant=iit)
    make_user("nitdbt.admin@test.dev", role=models.UserRole.admin, tenant=nit)

    iit_section = _make_section(
        session, tenant=iit, code="IIT-ECE", dept_name="IIT ECE"
    )

    # The IIT teacher (staff can post to any section) raises a doubt.
    created = client.post(
        "/doubts",
        json={
            "section_id": iit_section.id,
            "title": "IIT only doubt",
            "body": "Explain normalization",
        },
        headers=token_header("iitdbt.teach@test.dev"),
    )
    assert created.status_code == 201, created.text
    iit_doubt_id = created.json()["id"]

    # The NIT admin's governance list shows ONLY NIT doubts (none here).
    nit_list = client.get(
        "/doubts", headers=token_header("nitdbt.admin@test.dev")
    )
    assert nit_list.status_code == 200
    assert nit_list.json() == []

    # The NIT admin cannot open the IIT doubt by id -> hidden as 404.
    cross = client.get(
        f"/doubts/{iit_doubt_id}",
        headers=token_header("nitdbt.admin@test.dev"),
    )
    assert cross.status_code == 404, cross.text


def test_departments_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    """Departments are unique *per institute* and never leak across tenants.

    Two institutes can each create a 'Computer Science' / 'CSE' department
    (previously this was globally unique), and each admin's listing shows only
    their own institute's departments.
    """
    iit = make_tenant(slug="iit-dept", name="IIT Dept")
    nit = make_tenant(slug="nit-dept", name="NIT Dept")

    make_user("iitdept.admin@test.dev", role=models.UserRole.admin, tenant=iit)
    make_user("nitdept.admin@test.dev", role=models.UserRole.admin, tenant=nit)

    # Both institutes create the SAME name/code -> allowed (per-tenant unique).
    iit_create = client.post(
        "/admin/departments",
        json={"name": "Computer Science", "code": "CSE"},
        headers=token_header("iitdept.admin@test.dev"),
    )
    assert iit_create.status_code == 201, iit_create.text
    nit_create = client.post(
        "/admin/departments",
        json={"name": "Computer Science", "code": "CSE"},
        headers=token_header("nitdept.admin@test.dev"),
    )
    assert nit_create.status_code == 201, nit_create.text

    # Re-creating the same code within the SAME institute still conflicts.
    dup = client.post(
        "/admin/departments",
        json={"name": "Comp Sci 2", "code": "CSE"},
        headers=token_header("iitdept.admin@test.dev"),
    )
    assert dup.status_code == 409, dup.text

    # Each admin sees ONLY their own institute's department.
    iit_list = client.get(
        "/admin/departments", headers=token_header("iitdept.admin@test.dev")
    )
    assert iit_list.status_code == 200
    assert [d["code"] for d in iit_list.json()] == ["CSE"]
    assert len(iit_list.json()) == 1

    nit_list = client.get(
        "/admin/departments", headers=token_header("nitdept.admin@test.dev")
    )
    assert nit_list.status_code == 200
    assert len(nit_list.json()) == 1


def test_applications_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    """An application is bound to its drive's institute: each student sees only
    their own institute's applications, and a cross-tenant TPO can't view the
    applicants on another institute's drive (hidden as 404)."""
    iit = make_tenant(slug="iit-app", name="IIT Apply")
    nit = make_tenant(slug="nit-app", name="NIT Apply")

    make_user("iitap.tpo@test.dev", role=models.UserRole.tpo, tenant=iit)
    make_user("iitap.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("nitap.tpo@test.dev", role=models.UserRole.tpo, tenant=nit)
    make_user("nitap.stu@test.dev", role=models.UserRole.student, tenant=nit)

    # Each TPO posts an open drive (no thresholds -> any student is eligible).
    iit_drive = client.post(
        "/drives",
        json={"company_name": "Acme", "role_title": "Backend Engineer"},
        headers=token_header("iitap.tpo@test.dev"),
    )
    assert iit_drive.status_code == 201, iit_drive.text
    iit_drive_id = iit_drive.json()["id"]

    nit_drive = client.post(
        "/drives",
        json={"company_name": "Globex", "role_title": "Data Engineer"},
        headers=token_header("nitap.tpo@test.dev"),
    )
    assert nit_drive.status_code == 201, nit_drive.text
    nit_drive_id = nit_drive.json()["id"]

    # Each student applies to their own institute's drive.
    assert (
        client.post(
            f"/drives/{iit_drive_id}/apply",
            headers=token_header("iitap.stu@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/drives/{nit_drive_id}/apply",
            headers=token_header("nitap.stu@test.dev"),
        ).status_code
        == 201
    )

    # Each student's /me/applications shows ONLY their own application.
    iit_apps = client.get(
        "/drives/me/applications", headers=token_header("iitap.stu@test.dev")
    )
    assert iit_apps.status_code == 200
    assert len(iit_apps.json()) == 1

    # The NIT TPO cannot view applicants on IIT's drive -> 404 (drive hidden).
    cross = client.get(
        f"/drives/{iit_drive_id}/applications",
        headers=token_header("nitap.tpo@test.dev"),
    )
    assert cross.status_code == 404, cross.text


def test_calendar_events_are_tenant_scoped(
    client, make_user, make_tenant, token_header
):
    """One institute's calendar entries never leak to another institute.

    Both admins post an audience="all" entry; an IIT reader (student) and the
    IIT admin governance view must each see ONLY the IIT entry.
    """
    iit = make_tenant(slug="iit-cal", name="IIT Cal")
    nit = make_tenant(slug="nit-cal", name="NIT Cal")

    make_user("iitcal.admin@test.dev", role=models.UserRole.admin, tenant=iit)
    make_user("iitcal.stu@test.dev", role=models.UserRole.student, tenant=iit)
    make_user("nitcal.admin@test.dev", role=models.UserRole.admin, tenant=nit)

    assert (
        client.post(
            "/calendar",
            json={
                "title": "IIT Fest",
                "event_date": "2026-07-01",
                "category": "event",
                "audience": "all",
            },
            headers=token_header("iitcal.admin@test.dev"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/calendar",
            json={
                "title": "NIT Fest",
                "event_date": "2026-07-02",
                "category": "event",
                "audience": "all",
            },
            headers=token_header("nitcal.admin@test.dev"),
        ).status_code
        == 201
    )

    # IIT student sees only IIT's entry (despite both being audience "all").
    resp = client.get(
        "/calendar", headers=token_header("iitcal.stu@test.dev")
    )
    assert resp.status_code == 200, resp.text
    assert [e["title"] for e in resp.json()] == ["IIT Fest"]

    # IIT admin's full governance view is likewise tenant-bounded.
    admin_resp = client.get(
        "/calendar", headers=token_header("iitcal.admin@test.dev")
    )
    assert admin_resp.status_code == 200, admin_resp.text
    assert [e["title"] for e in admin_resp.json()] == ["IIT Fest"]
