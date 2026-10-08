from flask import request

ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365


def remember_preference(response, name, value):
    response.set_cookie(
        name,
        value,
        max_age=ONE_YEAR_IN_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
    )
    return response
