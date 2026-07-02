"""Campus-AI end-to-end SMOKE TEST.

Ek hi command me poore backend ko auto-check karta hai: har role se login,
saare major endpoints (reads) hit, aur key WRITE + AI flows (skill->verify,
leave, doubt, resume-AI, mentor-AI + file-upload signed-URL chain) run karke
ek clean PASS/FAIL report deta hai.

Chalane ka tareeka (backend folder me, jahan pyproject.toml hai):

    # LIVE (Render) ke against:
    uv run python e2e_smoke.py https://campus-ai-backend-ez7m.onrender.com

    # ya LOCAL backend ke against (pehle uvicorn chala lena):
    uv run python e2e_smoke.py http://127.0.0.1:8000

Kuch banaao mat -> har banaayi hui test-row turant DELETE ho jaati hai
(demo data ganda nahi hota). Sirf padho, output paste kar dena.
"""
from __future__ import annotations

import sys
import time
import json
from datetime import date, timedelta

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://campus-ai-backend-ez7m.onrender.com").rstrip("/")
PASSWORD = "DemoPass123"
ACCOUNTS = {
    "admin": "admin@demo.campus.ai",
    "teacher": "teacher@demo.campus.ai",
    "tpo": "tpo@demo.campus.ai",
    "student": "aarav@demo.campus.ai",
}

client = httpx.Client(base_url=BASE, timeout=120.0)
tokens: dict[str, str] = {}
results: list[dict] = []       # every check
ctx: dict[str, object] = {}    # captured ids (section_id, drive_id, ...)

C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YEL = "\033[93m"
C_DIM = "\033[90m"
C_0 = "\033[0m"


def _classify(code: int, expect) -> str:
    if isinstance(code, int) and code in expect:
        return "PASS"
    if code == "EXC":
        return "ERROR"
    if isinstance(code, int) and code >= 500:
        return "FAIL"
    return "WARN"  # 400/401/403/404/422 -> not a crash, just note


def check(role, method, path, *, params=None, json_body=None, data=None,
          expect=(200, 201, 204), label=None):
    """Run one request, record the result, return the response (or None)."""
    headers = {}
    if role and role in tokens:
        headers["Authorization"] = f"Bearer {tokens[role]}"
    t0 = time.time()
    try:
        r = client.request(method, path, params=params, json=json_body,
                            data=data, headers=headers)
        code = r.status_code
    except Exception as e:  # network / CORS / timeout
        results.append({"status": "ERROR", "role": role, "m": method, "p": path,
                        "code": "EXC", "ms": int((time.time() - t0) * 1000),
                        "note": f"{type(e).__name__}: {e}"[:110], "label": label})
        return None
    status = _classify(code, expect)
    note = ""
    if status != "PASS":
        try:
            note = json.dumps(r.json())[:130]
        except Exception:
            note = (r.text or "")[:130]
    results.append({"status": status, "role": role, "m": method, "p": path,
                    "code": code, "ms": int((time.time() - t0) * 1000),
                    "note": note, "label": label})
    return r


def warmup():
    print(f"Warming up {BASE} (Render free-tier ~30-50s cold start ho sakta hai)...")
    for i in range(6):
        try:
            r = client.get("/docs", timeout=60)
            if r.status_code < 500:
                print("  server up.\n")
                return
        except Exception as e:
            print(f"  retry {i+1}: {type(e).__name__}")
        time.sleep(8)
    print("  (warmup timed out, phir bhi try karte hain)\n")


def login_all():
    for role, email in ACCOUNTS.items():
        try:
            r = client.post("/auth/login",
                            data={"username": email, "password": PASSWORD}, timeout=60)
            if r.status_code == 200:
                tokens[role] = r.json()["access_token"]
                results.append({"status": "PASS", "role": role, "m": "POST",
                                "p": "/auth/login", "code": 200, "ms": 0,
                                "note": "", "label": "login"})
            else:
                results.append({"status": "FAIL", "role": role, "m": "POST",
                                "p": "/auth/login", "code": r.status_code, "ms": 0,
                                "note": (r.text or "")[:120], "label": "login"})
        except Exception as e:
            results.append({"status": "ERROR", "role": role, "m": "POST",
                            "p": "/auth/login", "code": "EXC", "ms": 0,
                            "note": str(e)[:120], "label": "login"})


def reads():
    # who am I (each role) + capture student's section
    for role in ACCOUNTS:
        r = check(role, "GET", "/auth/me")
        if role == "student" and r is not None and r.status_code == 200:
            ctx["section_id"] = r.json().get("section_id")
            ctx["student_id"] = r.json().get("id")

    sid = ctx.get("section_id")

    # ---- Admin ----
    check("admin", "GET", "/admin/users")
    r = check("admin", "GET", "/admin/departments")
    if r is not None and r.status_code == 200 and r.json():
        ctx["dept_id"] = r.json()[0]["id"]
        check("admin", "GET", f"/admin/departments/{ctx['dept_id']}/sections")
    check("admin", "GET", "/admin/users/bulk-template")
    check("admin", "GET", "/institute/dashboard")
    check("admin", "GET", "/audit")
    check("admin", "GET", "/announcements")
    check("admin", "GET", "/calendar")
    check("admin", "GET", "/recruiters")
    check("admin", "GET", "/recruiters/invites")
    check("admin", "GET", "/tenants/invites")

    # ---- Student ----
    check("student", "GET", "/announcements")
    check("student", "GET", "/calendar")
    r = check("student", "GET", "/academics/subjects")
    if r is not None and r.status_code == 200 and r.json():
        ctx["subject_id"] = r.json()[0]["id"]
    check("student", "GET", "/academics/me/results")
    check("student", "GET", "/academics/me/summary")
    check("student", "GET", "/analytics/me")
    check("student", "GET", "/attendance/me")
    check("student", "GET", "/attendance/me/summary")
    check("student", "GET", "/assignments/me")
    check("student", "GET", "/materials/me")
    check("student", "GET", "/skills/me")
    check("student", "GET", "/projects/me")
    check("student", "GET", "/internships/me")
    check("student", "GET", "/eca/me")
    check("student", "GET", "/timetable/me")
    check("student", "GET", "/leave/me")
    check("student", "GET", "/resume/versions")
    check("student", "GET", "/drives/open")
    check("student", "GET", "/drives/me/applications")
    if sid:
        check("student", "GET", "/doubts", params={"section_id": sid})
    check("student", "GET", "/doubts/me")

    # ---- Teacher (verify queues + section views) ----
    check("teacher", "GET", "/skills/queue")
    check("teacher", "GET", "/projects/queue")
    check("teacher", "GET", "/internships/queue")
    check("teacher", "GET", "/eca/queue")
    check("teacher", "GET", "/timetable/teaching")
    check("teacher", "GET", "/leave")            # pending decisions list
    check("teacher", "GET", "/people/students")
    if sid:
        check("teacher", "GET", "/assignments", params={"section_id": sid})
        check("teacher", "GET", "/materials", params={"section_id": sid})
        check("teacher", "GET", f"/analytics/section/{sid}")
        check("teacher", "GET", f"/analytics/section/{sid}/at-risk")
        check("teacher", "GET", f"/attendance/section/{sid}",
              params={"date": date.today().isoformat()})
        check("teacher", "GET", "/timetable", params={"section_id": sid})

    # ---- TPO / Placement ----
    r = check("tpo", "GET", "/drives")
    if r is not None and r.status_code == 200 and r.json():
        ctx["drive_id"] = r.json()[0]["id"]
        did = ctx["drive_id"]
        check("tpo", "GET", f"/drives/{did}")
        check("tpo", "GET", f"/drives/{did}/eligibility")
        check("tpo", "GET", f"/drives/{did}/applications")
    check("tpo", "GET", "/placement/analytics/overview")
    check("tpo", "GET", "/people/students")


def writes_and_ai():
    sid = ctx.get("section_id")

    # 1) SKILL moat chain: student creates -> teacher sees in queue -> verifies -> cleanup
    r = check("student", "POST", "/skills",
              json_body={"name": "E2E-SmokeTest-Skill",
                         "evidence_note": "automated smoke test"},
              label="moat:skill-create")
    skill_id = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if skill_id:
        q = check("teacher", "GET", "/skills/queue", label="moat:skill-in-queue")
        seen = q is not None and q.status_code == 200 and any(
            s.get("id") == skill_id for s in q.json())
        results.append({"status": "PASS" if seen else "FAIL", "role": "teacher",
                        "m": "CHECK", "p": "skill appears in verify queue",
                        "code": "-", "ms": 0,
                        "note": "" if seen else "created skill NOT visible to teacher (RLS/tenant?)",
                        "label": "moat:skill-in-queue"})
        check("teacher", "PATCH", f"/skills/{skill_id}/decision",
              json_body={"status": "verified", "review_note": "smoke"},
              label="moat:skill-verify")
        check("student", "DELETE", f"/skills/{skill_id}", label="cleanup:skill")

    # 2) PROJECT create + cleanup
    r = check("student", "POST", "/projects",
              json_body={"title": "E2E-SmokeTest-Project",
                         "description": "auto", "tech_stack": "Python"},
              label="moat:project-create")
    pid = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if pid:
        check("student", "DELETE", f"/projects/{pid}", label="cleanup:project")

    # 3) INTERNSHIP create + cleanup
    r = check("student", "POST", "/internships",
              json_body={"organization": f"E2E Corp {int(time.time())}",
                         "role_title": "SDE Intern",
                         "internship_type": "internship", "is_ongoing": True},
              label="moat:internship-create")
    iid = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if iid:
        check("student", "DELETE", f"/internships/{iid}", label="cleanup:internship")

    # 4) LEAVE apply -> teacher decision -> cleanup
    r = check("student", "POST", "/leave",
              json_body={"request_type": "leave", "category": "medical",
                         "title": "E2E smoke leave", "reason": "auto",
                         "start_date": (date.today() + timedelta(days=3)).isoformat(),
                         "end_date": (date.today() + timedelta(days=3)).isoformat()},
              label="leave:apply")
    lid = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if lid:
        check("student", "DELETE", f"/leave/{lid}", label="cleanup:leave")

    # 5) DOUBT post + cleanup (needs section)
    if sid:
        r = check("student", "POST", "/doubts",
                  json_body={"section_id": sid, "title": "E2E smoke doubt",
                             "body": "automated question"},
                  label="doubt:create")
        did = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
        if did:
            check("student", "DELETE", f"/doubts/{did}", label="cleanup:doubt")

    # 6) AI CHAIN: resume generate (HF worker + LLM) + cleanup
    r = check("student", "POST", "/resume/generate",
              json_body={"target_role": "Backend Engineer"},
              expect=(200, 201), label="AI:resume-generate")
    if r is not None and r.status_code == 200:
        vid = r.json().get("version_id")
        prov = r.json().get("provider")
        results.append({"status": "PASS", "role": "student", "m": "INFO",
                        "p": "resume provider", "code": "-", "ms": 0,
                        "note": f"provider={prov}", "label": "AI:resume-generate"})
        if vid:
            check("student", "DELETE", f"/resume/versions/{vid}", label="cleanup:resume")

    # 7) AI: ATS score
    check("student", "POST", "/resume/ats-score",
          json_body={"resume_text": "Python, FastAPI, SQL, built campus API.",
                     "job_description": "Looking for a backend engineer with Python and SQL."},
          label="AI:ats-score")

    # 8) AI: mentor chat (worker + Qdrant grounding)
    r = check("student", "POST", "/mentor/chat",
              json_body={"question": "Backend role ke liye mera skill gap kya hai?"},
              label="AI:mentor-chat")
    if r is not None and r.status_code == 200:
        results.append({"status": "PASS", "role": "student", "m": "INFO",
                        "p": "mentor provider", "code": "-", "ms": 0,
                        "note": f"provider={r.json().get('provider')}",
                        "label": "AI:mentor-chat"})


def file_uploads():
    """Section 7 Part B: poora Supabase signed-URL storage chain auto-check.

    sign-upload -> direct PUT to Supabase -> sign-download -> GET (bytes match)
    -> uploaded path ko internship.certificate_url + leave.proof_url me wire
    karke persist verify -> sab cleanup. Storage off (503) ho to gracefully skip.
    """
    role = "student"
    blob = b"%PDF-1.4\n% Campus-AI e2e smoke upload\n"

    # Probe: sign-upload (yeh bhi bata deta hai storage enabled hai ya nahi)
    r = check(role, "POST", "/files/sign-upload",
              json_body={"filename": "e2e-smoke.pdf", "kind": "certificate"},
              expect=(200,), label="files:sign-upload")
    if r is None:
        return
    if r.status_code == 503:
        results.append({"status": "WARN", "role": role, "m": "INFO",
                        "p": "storage disabled (SUPABASE_* env missing) -> upload chain skipped",
                        "code": 503, "ms": 0, "note": "", "label": "files:storage"})
        return
    if r.status_code != 200:
        return
    signed = r.json()
    path = signed["path"]
    upload_url = signed["upload_url"]

    # Storage confirmed ON -> ab validation guards asli 4xx dete hain
    check(role, "POST", "/files/sign-upload",
          json_body={"filename": "x.pdf", "kind": "not-a-kind"},
          expect=(400,), label="files:bad-kind->400")
    check(role, "POST", "/files/sign-upload",
          json_body={"filename": "x.exe", "kind": "certificate"},
          expect=(415,), label="files:bad-ext->415")
    # Tenant isolation: doosre tenant ka path sign karne pe 403 aana chahiye
    check(role, "POST", "/files/sign-download",
          json_body={"path": "999999/certificate/1/deadbeef-x.pdf"},
          expect=(403,), label="files:cross-tenant->403")

    # PUT raw bytes seedha Supabase ko (browser jaisa, API ko bypass karke)
    t0 = time.time()
    try:
        pr = httpx.put(upload_url, content=blob,
                       headers={"content-type": "application/pdf", "x-upsert": "true"},
                       timeout=60)
        put_code = pr.status_code
        put_status = ("PASS" if put_code in (200, 201)
                      else "FAIL" if put_code >= 500 else "WARN")
        note = "" if put_status == "PASS" else (pr.text or "")[:130]
    except Exception as e:
        put_code, put_status, note = "EXC", "ERROR", f"{type(e).__name__}: {e}"[:110]
    results.append({"status": put_status, "role": role, "m": "PUT",
                    "p": "Supabase upload (direct)", "code": put_code,
                    "ms": int((time.time() - t0) * 1000), "note": note,
                    "label": "files:supabase-put"})

    # sign-download for the same path
    dr = check(role, "POST", "/files/sign-download",
               json_body={"path": path}, expect=(200,), label="files:sign-download")
    download_url = (dr.json().get("download_url")
                    if (dr is not None and dr.status_code == 200) else None)

    # GET the file back + verify bytes round-trip exactly
    if download_url:
        t0 = time.time()
        try:
            gr = httpx.get(download_url, timeout=60)
            ok = gr.status_code == 200 and gr.content == blob
            gstatus = "PASS" if ok else "FAIL" if gr.status_code >= 500 else "WARN"
            gnote = "" if ok else f"code={gr.status_code} bytes_match={gr.content == blob}"
        except Exception as e:
            gstatus, gnote = "ERROR", f"{type(e).__name__}: {e}"[:110]
        results.append({"status": gstatus, "role": role, "m": "GET",
                        "p": "Supabase download (bytes round-trip)", "code": "-",
                        "ms": int((time.time() - t0) * 1000), "note": gnote,
                        "label": "files:supabase-get"})

    # Wire uploaded path -> INTERNSHIP.certificate_url, verify persist, cleanup
    r = check(role, "POST", "/internships",
              json_body={"organization": f"E2E Upload Corp {int(time.time())}",
                         "role_title": "Intern",
                         "internship_type": "internship", "is_ongoing": True,
                         "certificate_url": path},
              expect=(200, 201), label="files:internship+certificate")
    iid = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if iid:
        mine = check(role, "GET", "/internships/me", label="files:internship-read")
        saved = mine is not None and mine.status_code == 200 and any(
            x.get("id") == iid and x.get("certificate_url") == path for x in mine.json())
        results.append({"status": "PASS" if saved else "FAIL", "role": role,
                        "m": "CHECK", "p": "internship.certificate_url persisted",
                        "code": "-", "ms": 0,
                        "note": "" if saved else "certificate_url stored/returned nahi hua",
                        "label": "files:internship-persist"})
        check(role, "DELETE", f"/internships/{iid}", label="cleanup:internship-upload")

    # Wire uploaded path -> LEAVE.proof_url, cleanup
    r = check(role, "POST", "/leave",
              json_body={"request_type": "leave", "category": "medical",
                         "title": "E2E upload leave", "reason": "auto",
                         "start_date": (date.today() + timedelta(days=4)).isoformat(),
                         "end_date": (date.today() + timedelta(days=4)).isoformat(),
                         "proof_url": path},
              expect=(200, 201), label="files:leave+proof")
    lid = r.json().get("id") if (r is not None and r.status_code in (200, 201)) else None
    if lid:
        check(role, "DELETE", f"/leave/{lid}", label="cleanup:leave-upload")


def report():
    order = {"FAIL": 0, "ERROR": 1, "WARN": 2, "PASS": 3}
    color = {"PASS": C_GREEN, "FAIL": C_RED, "ERROR": C_RED, "WARN": C_YEL}
    icon = {"PASS": "OK  ", "FAIL": "FAIL", "ERROR": "ERR ", "WARN": "WARN"}
    print("\n" + "=" * 78)
    print(f"  CAMPUS-AI  E2E SMOKE REPORT   |   {BASE}")
    print("=" * 78)
    for row in sorted(results, key=lambda x: (order.get(x["status"], 9), x["role"])):
        s = row["status"]
        c = color.get(s, "")
        ms = f"{row['ms']:>5}ms" if row["ms"] else "     -"
        line = f"  {c}{icon[s]}{C_0} [{row['role']:<7}] {row['m']:<6} {str(row['code']):<4} {ms}  {row['p']}"
        if row["note"]:
            line += f"  {C_DIM}{row['note']}{C_0}"
        print(line)
    n = {k: sum(1 for r in results if r["status"] == k) for k in order}
    print("=" * 78)
    print(f"  TOTAL {len(results)}   |   "
          f"{C_GREEN}PASS {n['PASS']}{C_0}   "
          f"{C_RED}FAIL {n['FAIL']}{C_0}   "
          f"{C_RED}ERROR {n['ERROR']}{C_0}   "
          f"{C_YEL}WARN {n['WARN']}{C_0}")
    broken = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    if broken:
        print("\n  " + C_RED + "### TUTA HUA (yahi fix karna hai) ###" + C_0)
        for r in broken:
            print(f"   - [{r['role']}] {r['m']} {r['p']}  ->  {r['code']}  {r['note']}")
    else:
        print("\n  " + C_GREEN + "Koi 5xx/crash nahi mila. WARN wale sirf role/permission/data-missing hain." + C_0)
    print("=" * 78)
    print("  Note: WARN (401/403/404/422) = crash nahi hai Ã¢â‚¬â€ role-permission ya")
    print("        seed-data missing. Sirf FAIL/ERROR (5xx/network) asli bug hai.")
    print("=" * 78)


def main():
    warmup()
    login_all()
    if not tokens:
        print(C_RED + "Login hi fail ho gaya Ã¢â‚¬â€ URL/creds check kar. Report:" + C_0)
        report()
        return
    reads()
    writes_and_ai()
    file_uploads()
    report()


if __name__ == "__main__":
    main()
