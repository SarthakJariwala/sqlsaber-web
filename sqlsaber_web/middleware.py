from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import redirect

from .user_config_store import compute_user_config_status


class RequireUserConfigurationMiddleware:
    """Redirect authenticated users to /settings until configured."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if user is not None and getattr(user, "is_authenticated", False):
            status = compute_user_config_status(user)
            needs_onboarding = not status.is_configured

            if needs_onboarding:
                # Allow the onboarding/settings page and its API endpoints.
                path = request.path or ""
                allowed_prefixes = (
                    "/settings/",
                    "/accounts/",
                    "/admin/",
                    "/static/",
                    "/api/user/",
                )

                if not path.startswith(allowed_prefixes):
                    if path.startswith("/api/"):
                        return JsonResponse(
                            {
                                "error": "Configuration required",
                                "redirect": "/settings/",
                            },
                            status=409,
                        )
                    return redirect("/settings/")

        return self.get_response(request)
