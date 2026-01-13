"""Services module for sqlsaber_web business logic."""

from .api_helpers import api_login_required, key_preview, parse_json_body
from .serializers import (
    build_thread_with_messages_props,
    build_threads_list_props,
    build_user_config_props,
)
from .threads import (
    get_thread_for_user,
    serialize_thread,
    serialize_thread_summary,
    threads_queryset_for_user,
)
from .user_config import (
    SQLSaberRuntimeConfig,
    UserConfigStatus,
    compute_user_config_status,
    ensure_user_defaults,
    get_or_create_user_settings,
    get_runtime_config_for_thread_id,
    get_selected_or_default_db,
    get_selected_or_default_model,
    parse_provider,
)

__all__ = [
    # API helpers
    "api_login_required",
    "key_preview",
    "parse_json_body",
    # Serializers
    "build_thread_with_messages_props",
    "build_threads_list_props",
    "build_user_config_props",
    # Thread services
    "get_thread_for_user",
    "serialize_thread",
    "serialize_thread_summary",
    "threads_queryset_for_user",
    # User config services
    "SQLSaberRuntimeConfig",
    "UserConfigStatus",
    "compute_user_config_status",
    "ensure_user_defaults",
    "get_or_create_user_settings",
    "get_runtime_config_for_thread_id",
    "get_selected_or_default_db",
    "get_selected_or_default_model",
    "parse_provider",
]
