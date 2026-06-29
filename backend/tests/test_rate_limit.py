"""Rate limiting: /auth/login is capped per client IP and returns 429 past it.

This guards the slowapi layer added in Step 34 against regressions. We send a
dedicated X-Forwarded-For IP so this test's burst lives in its own bucket and
cannot exhaust the quota for other tests that also log in.
"""


def test_login_rate_limited_after_quota(client):
    headers = {"X-Forwarded-For": "203.0.113.77"}
    payload = {"username": "ghost@test.dev", "password": "whatever"}

    statuses = [
        client.post("/auth/login", data=payload, headers=headers).status_code
        for _ in range(35)
    ]

    # The login cap is 30/minute: early attempts are normal auth failures (401),
    # then slowapi starts returning 429 once the quota is exhausted.
    assert 429 in statuses
    assert statuses.count(401) >= 1
    # 429s must come AFTER the allowed window, never on the very first request.
    assert statuses[0] == 401
