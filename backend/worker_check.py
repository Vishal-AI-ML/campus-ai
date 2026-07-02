"""Campus-AI  AI-WORKER  direct health check.

Backend ke through nahi, seedha AI worker (HF Space) ke endpoints ko hit karta
hai taaki pata chale worker khud zinda + sahi jawab de raha hai ya nahi:
  - /score/proof   (skill claim scoring)      <- background me use hota hai
  - /score/proof   (project claim scoring)     <- /projects wala path
  - /resume/ats-score
  - /resume/draft
  - /mentor/chat

WORKER_URL + WORKER_TOKEN kahan se lega (is order me):
  1) command-line args:  uv run python worker_check.py <URL> <TOKEN>
  2) environment vars:   AI_WORKER_URL / AI_WORKER_TOKEN
  3) backend .env file   (AI_WORKER_URL=... / AI_WORKER_TOKEN=...)

Example:
  uv run python worker_check.py https://vishalaigenai-campus-ai-worker.hf.space <TOKEN>
"""
from __future__ import annotations

import os
import sys
import time
import json

import httpx


def _load_dotenv(path: str = ".env") -> dict:
    vals: dict[str, str] = {}
    if not os.path.exists(path):
        return vals
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


_env = _load_dotenv()
URL = (sys.argv[1] if len(sys.argv) > 1
       else os.getenv("AI_WORKER_URL") or _env.get("AI_WORKER_URL", "")).rstrip("/")
TOKEN = (sys.argv[2] if len(sys.argv) > 2
         else os.getenv("AI_WORKER_TOKEN") or _env.get("AI_WORKER_TOKEN", ""))

if not URL:
    print("AI_WORKER_URL nahi mila. Aise chala:\n"
          "  uv run python worker_check.py <WORKER_URL> <WORKER_TOKEN>")
    sys.exit(1)

HEADERS = {"X-Worker-Token": TOKEN} if TOKEN else {}
client = httpx.Client(base_url=URL, timeout=120.0)
results: list[dict] = []

C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YEL = "\033[93m"
C_DIM = "\033[90m"
C_0 = "\033[0m"

# A minimal-but-realistic verified profile for draft/chat endpoints.
SAMPLE_PROFILE = {
    "name": "Aarav Sharma",
    "target_role": "Backend Engineer",
    "cgpa": 8.2,
    "skills": [{"name": "FastAPI", "ai_score": 80}, {"name": "PostgreSQL", "ai_score": 75}],
    "projects": [{"title": "Campus API", "contribution": "Owner", "tech_stack": "FastAPI, PG"}],
    "internships": [{"organization": "Acme", "role_title": "SDE Intern"}],
}


def probe(label, method, path, *, json_body=None, expect=(200, 201),
          want_key=None):
    t0 = time.time()
    try:
        r = client.request(method, path, json=json_body, headers=HEADERS)
        code = r.status_code
    except Exception as e:
        results.append({"status": "ERROR", "label": label, "m": method, "p": path,
                        "code": "EXC", "ms": int((time.time() - t0) * 1000),
                        "note": f"{type(e).__name__}: {e}"[:120]})
        return None
    ok = code in expect
    note = ""
    body = None
    try:
        body = r.json()
    except Exception:
        body = None
    if ok and want_key and (not isinstance(body, dict) or want_key not in body):
        ok = False
        note = f"missing '{want_key}' in reply: {json.dumps(body)[:100]}"
    if ok and want_key:
        note = f"{want_key}={body.get(want_key)}" + (
            f", provider={body.get('provider')}" if isinstance(body, dict) and body.get("provider") else "")
    if not ok and not note:
        note = (json.dumps(body) if body is not None else r.text)[:120]
    status = "PASS" if ok else ("FAIL" if (isinstance(code, int) and code >= 500) else "WARN")
    results.append({"status": status, "label": label, "m": method, "p": path,
                    "code": code, "ms": int((time.time() - t0) * 1000), "note": note})
    return body


def main():
    print(f"Checking AI worker: {URL}")
    print(f"Token: {'set (' + str(len(TOKEN)) + ' chars)' if TOKEN else 'NOT SET (worker 401 de sakta hai)'}")
    print("HF Space sleep se uth raha ho to pehla call slow ho sakta hai...\n")

    # 1) liveness (HF spaces me / ya /health me se koi ek chalta hai)
    probe("liveness /", "GET", "/", expect=(200, 404, 405))
    probe("liveness /health", "GET", "/health", expect=(200, 404))

    # 2) skill proof scoring (background path for /skills)
    probe("score skill", "POST", "/score/proof",
          json_body={"claim_type": "skill", "title": "FastAPI",
                     "evidence_url": None, "evidence_note": "Built a REST API"},
          want_key="score")

    # 3) project proof scoring (background path for /projects) -- yahi 502 wala area
    probe("score project", "POST", "/score/proof",
          json_body={"claim_type": "project", "title": "Campus API - Owner",
                     "evidence_url": "https://github.com/x/campus",
                     "evidence_note": "Owner - built auth + DB"},
          want_key="score")

    # 4) ATS score (exact schema known)
    probe("resume ats-score", "POST", "/resume/ats-score",
          json_body={"resume_text": "Python, FastAPI, SQL. Built campus API.",
                     "job_description": "Backend engineer with Python + SQL."},
          want_key="score")

    # 5) resume draft (profile shape approx; provider check)
    probe("resume draft", "POST", "/resume/draft",
          json_body={"profile": SAMPLE_PROFILE}, want_key="markdown")

    # 6) mentor chat
    probe("mentor chat", "POST", "/mentor/chat",
          json_body={"profile": SAMPLE_PROFILE,
                     "question": "Backend role ke liye mera skill gap kya hai?",
                     "history": []}, want_key="answer")

    # report
    color = {"PASS": C_GREEN, "FAIL": C_RED, "ERROR": C_RED, "WARN": C_YEL}
    icon = {"PASS": "OK  ", "FAIL": "FAIL", "ERROR": "ERR ", "WARN": "WARN"}
    order = {"FAIL": 0, "ERROR": 1, "WARN": 2, "PASS": 3}
    print("=" * 74)
    print(f"  AI-WORKER CHECK   |   {URL}")
    print("=" * 74)
    for r in sorted(results, key=lambda x: order.get(x["status"], 9)):
        c = color.get(r["status"], "")
        ms = f"{r['ms']:>6}ms"
        line = f"  {c}{icon[r['status']]}{C_0} {str(r['code']):<4} {ms}  {r['label']:<18} {r['m']} {r['p']}"
        if r["note"]:
            line += f"  {C_DIM}{r['note']}{C_0}"
        print(line)
    n = {k: sum(1 for r in results if r["status"] == k) for k in order}
    print("=" * 74)
    print(f"  {C_GREEN}PASS {n['PASS']}{C_0}  {C_RED}FAIL {n['FAIL']}{C_0}  "
          f"{C_RED}ERROR {n['ERROR']}{C_0}  {C_YEL}WARN {n['WARN']}{C_0}")
    print("=" * 74)
    print("  Note: 401/404 aaye to token/URL check kar. FAIL(5xx)/ERROR = worker bug.")
    print("=" * 74)


if __name__ == "__main__":
    main()
