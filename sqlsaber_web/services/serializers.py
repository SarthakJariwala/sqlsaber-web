"""Serialization functions for API and Inertia views."""

from django.contrib.auth.models import AbstractBaseUser

from sqlsaber_web.models import (
    Message,
    UserApiKey,
    UserDatabaseConnection,
    UserModelConfig,
    UserSettings,
)
from sqlsaber_web.services.api_helpers import key_preview
from sqlsaber_web.services.threads import (
    get_thread_for_user,
    serialize_thread,
    serialize_thread_summary,
    threads_queryset_for_user,
)
from sqlsaber_web.services.user_config import (
    compute_user_config_status,
    ensure_user_defaults,
    get_or_create_user_settings,
)


def build_user_config_props(user: AbstractBaseUser) -> dict:
    """Build user config props for API and Inertia views.

    Returns dict with: configured, onboarding_completed, defaults,
    database_connections, api_keys, model_configs
    """
    ensure_user_defaults(user)

    settings = get_or_create_user_settings(user)
    settings = UserSettings.objects.select_related(
        "default_database_connection",
        "default_model_config",
        "default_model_config__api_key",
    ).get(pk=settings.pk)

    status = compute_user_config_status(user)

    default_db_id = (
        settings.default_database_connection_id
        if settings.default_database_connection
        and settings.default_database_connection.is_active
        else None
    )

    default_model_id = (
        settings.default_model_config_id
        if settings.default_model_config
        and settings.default_model_config.is_active
        and settings.default_model_config.api_key.is_active
        else None
    )

    dbs = UserDatabaseConnection.objects.filter(user=user).order_by(
        "is_active",
        "name",
    )
    keys = UserApiKey.objects.filter(user=user).order_by(
        "is_active",
        "provider",
        "name",
        "id",
    )
    models = (
        UserModelConfig.objects.filter(user=user)
        .select_related("api_key")
        .order_by("is_active", "display_name")
    )

    return {
        "configured": status.is_configured,
        "onboarding_completed": status.onboarding_completed,
        "defaults": {
            "database_connection_id": default_db_id,
            "model_config_id": default_model_id,
        },
        "database_connections": [
            {
                "id": db.id,
                "name": db.name,
                "memory": db.memory or "",
                "is_active": db.is_active,
            }
            for db in dbs
        ],
        "api_keys": [
            {
                "id": key.id,
                "provider": key.provider,
                "name": key.name,
                "preview": key_preview(key.api_key),
                "is_active": key.is_active,
            }
            for key in keys
        ],
        "model_configs": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "provider": m.provider,
                "model_name": m.model_name,
                "api_key_id": m.api_key_id,
                "api_key_is_active": m.api_key.is_active,
                "is_active": m.is_active,
            }
            for m in models
        ],
    }


def build_threads_list_props(user: AbstractBaseUser) -> dict:
    """Build threads list props for API and Inertia views.

    Returns dict with: threads
    """
    threads = threads_queryset_for_user(user).order_by("-updated_at")
    return {"threads": [serialize_thread_summary(t) for t in threads]}


def build_thread_with_messages_props(
    user: AbstractBaseUser, thread_id: int
) -> dict | None:
    """Build thread with messages props for API and Inertia views.

    Returns dict with: thread, messages
    Returns None if thread not found.
    """
    thread = get_thread_for_user(user, thread_id)
    if thread is None:
        return None

    messages = Message.objects.filter(thread=thread).order_by("id")

    return {
        "thread": serialize_thread(thread),
        "messages": [
            {
                "id": msg.id,
                "type": msg.type,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }
