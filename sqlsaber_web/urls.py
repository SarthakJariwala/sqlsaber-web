"""URL configuration for project."""

from django.contrib import admin
from django.urls import include, path

from . import api, views

urlpatterns = [
    # Page routes
    path("", views.home, name="home"),
    path("threads/", views.thread_list, name="thread_list"),
    path("threads/<uuid:thread_id>/", views.thread_detail, name="thread_detail"),
    path("settings/", views.settings_page, name="settings"),
    # Settings mutations (Inertia-native)
    path("settings/db-connections/add/", views.settings_add_db, name="settings_add_db"),
    path(
        "settings/db-connections/<int:pk>/update/",
        views.settings_update_db,
        name="settings_update_db",
    ),
    path(
        "settings/db-connections/<int:pk>/set-active/",
        views.settings_set_db_active,
        name="settings_set_db_active",
    ),
    path(
        "settings/api-keys/add/",
        views.settings_add_api_key,
        name="settings_add_api_key",
    ),
    path(
        "settings/api-keys/<int:pk>/update/",
        views.settings_update_api_key,
        name="settings_update_api_key",
    ),
    path(
        "settings/api-keys/<int:pk>/set-active/",
        views.settings_set_api_key_active,
        name="settings_set_api_key_active",
    ),
    path("settings/models/add/", views.settings_add_model, name="settings_add_model"),
    path(
        "settings/models/<int:pk>/update/",
        views.settings_update_model,
        name="settings_update_model",
    ),
    path(
        "settings/models/<int:pk>/set-active/",
        views.settings_set_model_active,
        name="settings_set_model_active",
    ),
    path(
        "settings/config/update/",
        views.settings_update_config,
        name="settings_update_config",
    ),
    # Admin and auth
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    # API endpoints
    path("api/threads/", api.threads_api, name="api_threads"),
    path(
        "api/threads/<uuid:thread_id>/messages/",
        api.get_messages,
        name="api_get_messages",
    ),
    path(
        "api/threads/<uuid:thread_id>/continue/",
        api.continue_thread,
        name="api_continue_thread",
    ),
]
