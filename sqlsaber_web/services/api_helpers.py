"""API helper utilities for request handling and decorators."""

import json
from functools import wraps

from django.http import JsonResponse


def api_login_required(view_func):
    """Decorator that returns 401 JSON response for unauthenticated API requests."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)

    return _wrapped


def parse_json_body(request) -> tuple[dict | None, JsonResponse | None]:
    """Parse JSON from request body.

    Returns:
        Tuple of (data, None) on success or (None, error_response) on failure.
    """
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


def key_preview(value: str) -> str:
    """Return a masked preview of an API key, showing only the last 4 characters."""
    value = value or ""
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"
