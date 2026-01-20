"""Thread query and serialization services."""

from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet

from sqlsaber_web.models import Thread


def threads_queryset_for_user(user: AbstractBaseUser) -> QuerySet[Thread]:
    """Return a queryset of threads for the given user with related objects prefetched."""
    return Thread.objects.filter(user=user).select_related(
        "database_connection",
        "model_config",
    )


def get_thread_for_user(
    user: AbstractBaseUser,
    thread_id: UUID | str,
) -> Thread | None:
    """Retrieve a specific thread for a user, or None if not found."""
    try:
        return threads_queryset_for_user(user).get(pk=thread_id)
    except Thread.DoesNotExist:
        return None


def serialize_thread_summary(thread: Thread) -> dict:
    """Serialize thread for list views (without error details)."""
    db = getattr(thread, "database_connection", None)
    model = getattr(thread, "model_config", None)

    return {
        "id": str(thread.id),
        "title": thread.title,
        "status": thread.status,
        "database_connection_id": thread.database_connection_id,
        "database_connection_name": db.name if db else None,
        "database_connection_is_active": db.is_active if db else None,
        "model_config_id": thread.model_config_id,
        "model_config_display_name": model.display_name if model else None,
        "model_config_model_name": model.model_name if model else None,
        "model_config_is_active": model.is_active if model else None,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }


def serialize_thread(thread: Thread) -> dict:
    """Serialize thread with full details including error message."""
    return {
        **serialize_thread_summary(thread),
        "error": thread.error_message,
    }
