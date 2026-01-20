import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class UserApiKey(models.Model):
    """An API key for a specific model provider owned by a user.

    A user may have multiple API keys (e.g. OpenAI + Anthropic), and multiple
    keys per provider (e.g. work + personal).

    Keys can be "removed" by marking them inactive (soft delete).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sqlsaber_api_keys",
    )
    provider = models.CharField(max_length=50)  # e.g. "openai", "anthropic"
    name = models.CharField(max_length=255, blank=True, default="")
    api_key = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "provider"]),
            models.Index(fields=["user", "is_active"]),
        ]


class UserDatabaseConnection(models.Model):
    """A database connection string owned by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sqlsaber_database_connections",
    )
    name = models.CharField(max_length=255)
    connection_string = models.TextField()
    memory = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=Q(is_active=True),
                name="uniq_sqlsaber_user_db_connection_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "name"]),
            models.Index(fields=["user", "is_active"]),
        ]


class UserModelConfig(models.Model):
    """A configured SQLSaber model for a user.

    `model_name` must be in SQLSaber format: "provider:model".

    Each configured model references exactly one API key.

    Models can be "removed" by marking them inactive (soft delete).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sqlsaber_model_configs",
    )
    display_name = models.CharField(max_length=255)
    provider = models.CharField(max_length=50)  # Derived from model_name
    model_name = models.CharField(max_length=255)
    api_key = models.ForeignKey(
        UserApiKey,
        on_delete=models.PROTECT,
        related_name="model_configs",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "display_name"],
                condition=Q(is_active=True),
                name="uniq_sqlsaber_user_model_config_display_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "provider"]),
            models.Index(fields=["user", "display_name"]),
            models.Index(fields=["user", "is_active"]),
        ]


class UserSettings(models.Model):
    """User-scoped runtime configuration for SQLSaber."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sqlsaber_settings",
    )
    default_database_connection = models.ForeignKey(
        UserDatabaseConnection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    default_model_config = models.ForeignKey(
        UserModelConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Thread(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        ERROR = "error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="threads",
    )
    database_connection = models.ForeignKey(
        UserDatabaseConnection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="threads",
    )
    model_config = models.ForeignKey(
        UserModelConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="threads",
    )
    title = models.CharField(max_length=255, blank=True)
    content = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    class Type(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"
        THINKING = "thinking"
        TOOL_CALL = "tool_call"
        TOOL_RESULT = "tool_result"

    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    content = models.JSONField()
    type = models.CharField(
        max_length=50,
        choices=Type.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]
