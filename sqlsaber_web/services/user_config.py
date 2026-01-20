"""User configuration services for managing API keys, database connections, and model configs."""

from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser

from sqlsaber_web.models import (
    Thread,
    UserDatabaseConnection,
    UserModelConfig,
    UserSettings,
)


@dataclass(frozen=True)
class UserConfigStatus:
    """Status of a user's configuration completeness."""

    onboarding_completed: bool
    has_default_database: bool
    has_default_model: bool

    @property
    def is_configured(self) -> bool:
        return (
            self.onboarding_completed
            and self.has_default_database
            and self.has_default_model
        )


@dataclass(frozen=True)
class SQLSaberRuntimeConfig:
    """Runtime configuration needed to execute SQLSaber queries."""

    database_connection: str
    model_name: str
    api_key: str
    memory: str | None


def parse_provider(model_name: str) -> str:
    """Extract provider name from a model name in 'provider:model' format."""
    model_name = (model_name or "").strip()
    if ":" not in model_name:
        raise ValueError('model_name must be in the format "provider:model"')
    provider, _ = model_name.split(":", 1)
    provider = provider.strip()
    if not provider:
        raise ValueError('model_name must be in the format "provider:model"')
    return provider


def get_or_create_user_settings(user: AbstractBaseUser) -> UserSettings:
    """Get or create UserSettings for the given user."""
    settings, _ = UserSettings.objects.get_or_create(user=user)
    return settings


def compute_user_config_status(user: AbstractBaseUser) -> UserConfigStatus:
    """Compute the configuration status for a user."""
    settings = get_or_create_user_settings(user)
    settings = UserSettings.objects.select_related(
        "default_database_connection",
        "default_model_config",
        "default_model_config__api_key",
    ).get(pk=settings.pk)

    has_default_database = bool(
        settings.default_database_connection
        and settings.default_database_connection.is_active
    )

    has_default_model = bool(
        settings.default_model_config
        and settings.default_model_config.is_active
        and settings.default_model_config.api_key.is_active
    )

    return UserConfigStatus(
        onboarding_completed=bool(settings.onboarding_completed),
        has_default_database=has_default_database,
        has_default_model=has_default_model,
    )


def ensure_user_defaults(user: AbstractBaseUser) -> UserSettings:
    """Best-effort default selection for new users.

    If the user has at least one active DB/model and no defaults set, pick the
    first active entries.
    """
    settings = get_or_create_user_settings(user)

    updated_fields: list[str] = []

    if settings.default_database_connection_id is None:
        db = (
            UserDatabaseConnection.objects.filter(user=user, is_active=True)
            .order_by("created_at")
            .first()
        )
        if db is not None:
            settings.default_database_connection = db
            updated_fields.append("default_database_connection")

    if settings.default_model_config_id is None:
        model = (
            UserModelConfig.objects.filter(
                user=user,
                is_active=True,
                api_key__is_active=True,
            )
            .order_by("created_at")
            .first()
        )
        if model is not None:
            settings.default_model_config = model
            updated_fields.append("default_model_config")

    if updated_fields:
        settings.save(update_fields=[*updated_fields, "updated_at"])

    return settings


def get_selected_or_default_db(
    user: AbstractBaseUser,
    *,
    selected_id: int | None,
) -> UserDatabaseConnection | None:
    """Get the selected database connection or fall back to user's default."""
    settings = ensure_user_defaults(user)

    db_id = (
        selected_id
        if selected_id is not None
        else settings.default_database_connection_id
    )
    if not db_id:
        return None

    return UserDatabaseConnection.objects.filter(
        user=user,
        id=db_id,
        is_active=True,
    ).first()


def get_selected_or_default_model(
    user: AbstractBaseUser,
    *,
    selected_id: int | None,
) -> UserModelConfig | None:
    """Get the selected model config or fall back to user's default."""
    settings = ensure_user_defaults(user)

    model_id = (
        selected_id if selected_id is not None else settings.default_model_config_id
    )
    if not model_id:
        return None

    return (
        UserModelConfig.objects.filter(
            user=user,
            id=model_id,
            is_active=True,
            api_key__is_active=True,
        )
        .select_related("api_key")
        .first()
    )


def get_runtime_config_for_thread_id(thread_id: UUID | str) -> SQLSaberRuntimeConfig:
    """Build runtime configuration for executing a thread's query."""
    thread = Thread.objects.select_related(
        "user",
        "database_connection",
        "model_config",
        "model_config__api_key",
    ).get(pk=thread_id)

    ensure_user_defaults(thread.user)

    user_settings = UserSettings.objects.select_related(
        "default_database_connection",
        "default_model_config",
        "default_model_config__api_key",
    ).get(user=thread.user)

    db = None
    if thread.database_connection and thread.database_connection.is_active:
        db = thread.database_connection
    elif (
        user_settings.default_database_connection
        and user_settings.default_database_connection.is_active
    ):
        db = user_settings.default_database_connection

    if db is None:
        raise RuntimeError(
            "No active database connection configured. Add one in /settings."
        )

    model = None
    if (
        thread.model_config
        and thread.model_config.is_active
        and thread.model_config.api_key.is_active
    ):
        model = thread.model_config
    elif (
        user_settings.default_model_config
        and user_settings.default_model_config.is_active
        and user_settings.default_model_config.api_key.is_active
    ):
        model = user_settings.default_model_config

    if model is None:
        raise RuntimeError("No active model configured. Add one in /settings.")

    database_connection = (db.connection_string or "").strip()
    if not database_connection:
        raise RuntimeError("Database connection is empty. Update it in /settings.")

    api_key_value = (model.api_key.api_key or "").strip()
    if not api_key_value:
        raise RuntimeError("API key is missing for the selected model.")

    model_name = (model.model_name or "").strip()
    if not model_name:
        raise RuntimeError("Model name is missing for the selected model.")

    memory = (db.memory or "").strip() or None

    return SQLSaberRuntimeConfig(
        database_connection=database_connection,
        model_name=model_name,
        api_key=api_key_value,
        memory=memory,
    )
