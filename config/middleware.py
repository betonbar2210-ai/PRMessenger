import hashlib
import re

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import split_directive_names

from config.settings import LOGIN_URL

_NO_STORE = ("no-store", "no-cache")

_CSRF_INPUT_RE = re.compile(rb'name="csrfmiddlewaretoken" value="[^"]*"')
_CSRF_NORMALIZED = b'name="csrfmiddlewaretoken" value=""'


def _csrf_token(request) -> str:
    token = request.META.get("CSRF_COOKIE")
    if not token:
        token = request.COOKIES.get(settings.CSRF_COOKIE_NAME, "")
    return token or "no-csrf-token"


def _compute_etag(response, csrf_token: str) -> str:
    normalized = _CSRF_INPUT_RE.sub(_CSRF_NORMALIZED, response.content)
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(normalized)
    digest.update(b"\x00csrf:")
    digest.update(csrf_token.encode())
    return f'W/"{digest.hexdigest()}"'


class ClientCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.method not in ("GET", "HEAD"):
            return response
        if response.streaming or response.status_code != 200:
            return response

        cache_control = response.get("Cache-Control", "")
        directives = {name.lower() for name in split_directive_names(cache_control)}
        if directives & set(_NO_STORE):
            # Оставляем «private», если он был: кэш браузера не должен
            # раздавать страницу общим CDN-прокси.
            keep_private = "private" if "private" in directives else None
            response["Cache-Control"] = ", ".join(
                filter(None, [keep_private, "max-age=0", "must-revalidate"])
            )

        if not response.has_header("ETag"):
            response["ETag"] = _compute_etag(response, _csrf_token(request))
        return response


class BlockedUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        if user.__class__.objects.filter(pk=user.pk, is_blocked=True).exists():
            logout(request)
            return redirect(LOGIN_URL)
        return None


__all__ = ["BlockedUserMiddleware", "ClientCacheMiddleware"]
