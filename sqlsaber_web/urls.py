"""URL configuration for project."""

from django.contrib import admin
from django.urls import include, path

from . import api, views

urlpatterns = [
    # Page routes
    path("", views.home, name="home"),
    path("threads/", views.thread_list, name="thread_list"),
    path("threads/<int:thread_id>/", views.thread_detail, name="thread_detail"),
    path("settings/", views.settings_page, name="settings"),
    # Admin and auth
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    # API endpoints
    path("api/threads/", api.threads_api, name="api_threads"),
    path("api/threads/<int:thread_id>/", api.get_thread, name="api_get_thread"),
    path(
        "api/threads/<int:thread_id>/messages/",
        api.get_messages,
        name="api_get_messages",
    ),
    path(
        "api/threads/<int:thread_id>/continue/",
        api.continue_thread,
        name="api_continue_thread",
    ),
    # User configuration API
    path("api/user/config/", api.get_user_config, name="api_get_user_config"),
    path(
        "api/user/config/update/",
        api.update_user_settings,
        name="api_update_user_settings",
    ),
    # API keys
    path("api/user/api-keys/add/", api.add_api_key, name="api_add_api_key"),
    path(
        "api/user/api-keys/<int:key_id>/update/",
        api.update_api_key,
        name="api_update_api_key",
    ),
    path(
        "api/user/api-keys/<int:key_id>/set-active/",
        api.set_api_key_active,
        name="api_set_api_key_active",
    ),
    # Database connections
    path(
        "api/user/db-connections/add/",
        api.add_database_connection,
        name="api_add_database_connection",
    ),
    path(
        "api/user/db-connections/<int:connection_id>/update/",
        api.update_database_connection,
        name="api_update_database_connection",
    ),
    path(
        "api/user/db-connections/<int:connection_id>/set-active/",
        api.set_database_connection_active,
        name="api_set_database_connection_active",
    ),
    # Models
    path("api/user/models/add/", api.add_model_config, name="api_add_model_config"),
    path(
        "api/user/models/<int:model_id>/update/",
        api.update_model_config,
        name="api_update_model_config",
    ),
    path(
        "api/user/models/<int:model_id>/set-active/",
        api.set_model_config_active,
        name="api_set_model_config_active",
    ),
]
