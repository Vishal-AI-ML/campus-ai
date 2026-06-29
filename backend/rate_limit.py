"""Rate limiting for abuse-prone PUBLIC endpoints (slowapi).

Why this exists
---------------
The unauthenticated routes are the obvious abuse targets:
  * POST /auth/login            -> credential stuffing / password brute force
  * POST /auth/register         -> spam / fake-account floods
  * POST /leads, /feedback      -> marketing-form spam bots
  * POST /recruiters/accept-invite -> invite-token guessing

slowapi gives per-client request quotas with almost no code. It uses an
in-memory store, which is correct for our single Render instance. If we ever
scale to multiple instances, point `storage_uri` at Redis so the counters are
shared (otherwise each instance counts separately).

Why per-IP (and the campus-NAT caveat)
--------------------------------------
We key on the *real* client IP. Behind Render's proxy the socket peer is the
load balancer, so we read the left-most `X-Forwarded-For` hop and fall back to
the socket address for local/dev.

NOTE: a whole college can sit behind ONE public IP (NAT). So we deliberately do
NOT set a global default limit (that would throttle an entire campus together)
and we keep the login/register ceilings generous. The per-IP limits here are a
first line of defense against bots; true per-account brute-force protection
(lockout / exponential backoff keyed on the email) is a later hardening step.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Best-effort real client IP, proxy-aware.

    Render/Vercel sit in front of us, so the TCP peer is the proxy. The
    originating client is the left-most entry of `X-Forwarded-For`.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


# Shared limiter. No default_limits on purpose (see campus-NAT note above);
# limits are applied explicitly via @limiter.limit(...) on individual routes.
# headers_enabled => responses carry X-RateLimit-Limit / -Remaining / -Reset
# so clients (and we) can see the quota state.
limiter = Limiter(key_func=client_ip, headers_enabled=True)
