import logging
from typing import Optional, Tuple

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from config import settings

logger = logging.getLogger(__name__)

_SLIDING_WINDOW_LUA = r"""
local base = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local t = redis.call('TIME')
local now_us = (tonumber(t[1]) * 1000000) + tonumber(t[2])
local window_us = window * 1000000

local current_bucket_us = math.floor(now_us / window_us) * window_us
local prev_bucket_us = current_bucket_us - window_us

local current_key = base .. ':' .. tostring(current_bucket_us)
local prev_key = base .. ':' .. tostring(prev_bucket_us)

local curr = redis.call('INCR', current_key)
redis.call('EXPIRE', current_key, window * 2)

local prev = tonumber(redis.call('GET', prev_key) or '0')

local elapsed_us = now_us - current_bucket_us
local weight = (window_us - elapsed_us) / window_us
local total = (prev * weight) + curr

local remaining = limit - math.floor(total)
if remaining < 0 then remaining = 0 end

local allowed = 1
if total > limit then
  allowed = 0
  redis.call('DECR', current_key)
  curr = curr - 1
  total = (prev * weight) + curr
  remaining = limit - math.floor(total)
  if remaining < 0 then remaining = 0 end
end

local reset_after = math.ceil((window_us - elapsed_us) / 1000000)
if reset_after < 0 then reset_after = 0 end

local retry_after = 0
if allowed == 0 then retry_after = reset_after end

return {allowed, total, remaining, retry_after, reset_after, curr, prev}
"""


async def _sliding_window_check(
    redis_client,
    *,
    base_key: str,
    limit: int,
    window_seconds: int,
) -> Tuple[bool, int, int]:
    result = await redis_client.eval(_SLIDING_WINDOW_LUA, 1, base_key, limit, window_seconds)
    allowed = bool(int(result[0]))
    remaining = int(result[2])
    retry_after = int(result[3])
    reset_after = int(result[4])
    return allowed, remaining, (retry_after or reset_after)


def _get_client_id(request: Request) -> str:
    value = request.headers.get(settings.RATE_LIMIT_CLIENT_ID_HEADER)
    if value is None or not value.strip():
        return "anonymous"
    return value.strip()


def _get_ip(request: Request) -> str:
    if request.client is None or request.client.host is None:
        return "unknown"
    return request.client.host


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") != "http" or not settings.RATE_LIMIT_ENABLED:
            return await self.app(scope, receive, send)

        path = scope.get("path") or ""
        if path in {"/docs", "/redoc", "/openapi.json"}:
            return await self.app(scope, receive, send)

        request = Request(scope, receive=receive)
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client is None:
            if settings.RATE_LIMIT_FAIL_OPEN:
                return await self.app(scope, receive, send)
            response = JSONResponse({"detail": "Rate limiter unavailable."}, status_code=503)
            return await response(scope, receive, send)

        limit = settings.RATE_LIMIT_MAX_REQUESTS
        window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS

        client_id = _get_client_id(request)
        ip = _get_ip(request)

        try:
            client_allowed, client_remaining, client_retry = await _sliding_window_check(
                redis_client,
                base_key=f"rl:cid:{client_id}",
                limit=limit,
                window_seconds=window_seconds,
            )
            ip_allowed, ip_remaining, ip_retry = await _sliding_window_check(
                redis_client,
                base_key=f"rl:ip:{ip}",
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception as e:
            logger.warning(f"Rate limit check failed (fail_open={settings.RATE_LIMIT_FAIL_OPEN}): {e}")
            if settings.RATE_LIMIT_FAIL_OPEN:
                return await self.app(scope, receive, send)
            response = JSONResponse({"detail": "Rate limiter error."}, status_code=503)
            return await response(scope, receive, send)

        remaining = min(client_remaining, ip_remaining)
        reset_after = max(client_retry, ip_retry)
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_after),
            "X-RateLimit-Client-Remaining": str(client_remaining),
            "X-RateLimit-IP-Remaining": str(ip_remaining),
        }

        if not (client_allowed and ip_allowed):
            headers["Retry-After"] = str(reset_after)
            response = JSONResponse(
                {"detail": f"You are sending too many requests. Please wait {reset_after} seconds and try again."},
                status_code=429,
                headers=headers,
            )
            return await response(scope, receive, send)

        async def send_with_headers(message):
            if message.get("type") == "http.response.start":
                raw_headers = list(message.get("headers") or [])
                for k, v in headers.items():
                    raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
                message["headers"] = raw_headers
            await send(message)

        return await self.app(scope, receive, send_with_headers)
