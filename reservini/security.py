import re

from flask import request

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
SAFE_PATH = re.compile(r"/(?![/\\])[^\s\\]*")


def add_security_headers(response):
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def safe_next_url(next_url, fallback):
    if next_url and SAFE_PATH.fullmatch(next_url):
        return next_url
    return fallback
