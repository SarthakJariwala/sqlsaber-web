import json
from functools import wraps

from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Message,
    Thread,
    UserApiKey,
    UserDatabaseConnection,
    UserModelConfig,
    UserSettings,
)
from .tasks import run_sqlsaber_query
from .user_config_store import (
    compute_user_config_status,
    ensure_user_defaults,
    get_or_create_user_settings,
    parse_provider,
)


def api_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)

    return _wrapped


def _parse_json_body(request) -> tuple[dict | None, JsonResponse | None]:
    """Parse JSON from request body. Returns (data, None) on success or (None, error_response) on failure."""
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


def _threads_queryset_for_user(user):
    return Thread.objects.filter(user=user).select_related(
        "database_connection",
        "model_config",
    )


def _get_thread_for_user(user, thread_id: int) -> Thread | None:
    try:
        return _threads_queryset_for_user(user).get(pk=thread_id)
    except Thread.DoesNotExist:
        return None


def _serialize_thread_summary(thread: Thread) -> dict:
    """Serialize thread for list views (without error details)."""

    db = getattr(thread, "database_connection", None)
    model = getattr(thread, "model_config", None)

    return {
        "id": thread.id,
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


def _serialize_thread(thread: Thread) -> dict:
    """Serialize thread with full details including error message."""
    return {
        **_serialize_thread_summary(thread),
        "error": thread.error_message,
    }


def _get_selected_or_default_db(
    user,
    *,
    selected_id: int | None,
) -> UserDatabaseConnection | None:
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


def _get_selected_or_default_model(
    user,
    *,
    selected_id: int | None,
) -> UserModelConfig | None:
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


def _key_preview(value: str) -> str:
    value = value or ""
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


@api_login_required
def threads_api(request):
    """Handle GET (list threads) and POST (create thread) on /api/threads/."""
    if request.method == "GET":
        threads = _threads_queryset_for_user(request.user).order_by("-updated_at")
        return JsonResponse(
            {"threads": [_serialize_thread_summary(t) for t in threads]}
        )
    if request.method == "POST":
        return create_thread(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)


def create_thread(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    data, error = _parse_json_body(request)
    if error:
        return error

    prompt = (data.get("prompt", "") or "").strip()
    if not prompt:
        return JsonResponse({"error": "prompt is required"}, status=400)

    database_connection_id = data.get("database_connection_id")
    model_config_id = data.get("model_config_id")

    if database_connection_id is not None and not isinstance(
        database_connection_id, int
    ):
        return JsonResponse(
            {"error": "database_connection_id must be an integer"}, status=400
        )
    if model_config_id is not None and not isinstance(model_config_id, int):
        return JsonResponse(
            {"error": "model_config_id must be an integer"}, status=400
        )

    db = _get_selected_or_default_db(
        request.user,
        selected_id=database_connection_id,
    )
    model = _get_selected_or_default_model(
        request.user,
        selected_id=model_config_id,
    )

    if db is None or model is None:
        return JsonResponse(
            {"error": "Configuration required", "redirect": "/settings/"},
            status=409,
        )

    thread = Thread.objects.create(
        user=request.user,
        title=prompt[:100],
        content={},
        status=Thread.Status.PENDING,
        database_connection=db,
        model_config=model,
    )

    Message.objects.create(
        thread=thread,
        type=Message.Type.USER,
        content={"text": prompt},
    )

    run_sqlsaber_query.defer(thread_id=thread.id, prompt=prompt)

    return JsonResponse({"id": thread.id})


@require_GET
@api_login_required
def get_thread(request, thread_id: int):
    thread = _get_thread_for_user(request.user, thread_id)
    if thread is None:
        return JsonResponse({"error": "Thread not found"}, status=404)

    return JsonResponse(_serialize_thread(thread))


@require_GET
@api_login_required
def get_messages(request, thread_id: int):
    thread = _get_thread_for_user(request.user, thread_id)
    if thread is None:
        return JsonResponse({"error": "Thread not found"}, status=404)

    after_id = request.GET.get("after")

    messages = Message.objects.filter(thread=thread)
    if after_id:
        try:
            messages = messages.filter(id__gt=int(after_id))
        except ValueError:
            return JsonResponse({"error": "Invalid after parameter"}, status=400)

    messages = messages.order_by("id")

    return JsonResponse(
        {
            "thread": _serialize_thread(thread),
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
    )


@require_POST
@api_login_required
def continue_thread(request, thread_id: int):
    """Continue an existing thread with a follow-up message."""
    data, error = _parse_json_body(request)
    if error:
        return error

    prompt = (data.get("prompt", "") or "").strip()
    if not prompt:
        return JsonResponse({"error": "prompt is required"}, status=400)

    database_connection_id = data.get("database_connection_id")
    model_config_id = data.get("model_config_id")

    if database_connection_id is not None and not isinstance(
        database_connection_id, int
    ):
        return JsonResponse(
            {"error": "database_connection_id must be an integer"}, status=400
        )
    if model_config_id is not None and not isinstance(model_config_id, int):
        return JsonResponse(
            {"error": "model_config_id must be an integer"}, status=400
        )

    thread = _get_thread_for_user(request.user, thread_id)
    if thread is None:
        return JsonResponse({"error": "Thread not found"}, status=404)

    if thread.status == Thread.Status.RUNNING:
        return JsonResponse(
            {
                "error": "Thread is currently running. Please wait for completion."
            },
            status=409,
        )
    if thread.status == Thread.Status.PENDING:
        return JsonResponse({"error": "Thread has not started yet."}, status=409)

    db = _get_selected_or_default_db(
        request.user,
        selected_id=database_connection_id,
    )
    model = _get_selected_or_default_model(
        request.user,
        selected_id=model_config_id,
    )

    if db is None or model is None:
        return JsonResponse(
            {"error": "Configuration required", "redirect": "/settings/"},
            status=409,
        )

    if not thread.content or not isinstance(thread.content, list):
        return JsonResponse(
            {"error": "No message history available for this thread."},
            status=400,
        )

    Message.objects.create(
        thread=thread,
        type=Message.Type.USER,
        content={"text": prompt},
    )

    thread.database_connection = db
    thread.model_config = model
    thread.status = Thread.Status.PENDING
    thread.save(
        update_fields=[
            "database_connection",
            "model_config",
            "status",
            "updated_at",
        ]
    )

    run_sqlsaber_query.defer(
        thread_id=thread.id,
        prompt=prompt,
        message_history=thread.content,
    )

    return JsonResponse({"id": thread.id, "status": "queued"})


@require_GET
@api_login_required
def get_user_config(request):
    ensure_user_defaults(request.user)

    settings = get_or_create_user_settings(request.user)
    settings = UserSettings.objects.select_related(
        "default_database_connection",
        "default_model_config",
        "default_model_config__api_key",
    ).get(pk=settings.pk)

    status = compute_user_config_status(request.user)

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

    dbs = UserDatabaseConnection.objects.filter(user=request.user).order_by(
        "is_active",
        "name",
    )
    keys = UserApiKey.objects.filter(user=request.user).order_by(
        "is_active",
        "provider",
        "name",
        "id",
    )
    models = (
        UserModelConfig.objects.filter(user=request.user)
        .select_related("api_key")
        .order_by("is_active", "display_name")
    )

    return JsonResponse(
        {
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
                    "preview": _key_preview(key.api_key),
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
    )


@require_POST
@api_login_required
def add_api_key(request):
    data, error = _parse_json_body(request)
    if error:
        return error

    provider = (data.get("provider", "") or "").strip().lower()
    name = (data.get("name", "") or "").strip()
    api_key = (data.get("api_key", "") or "").strip()

    if not provider:
        return JsonResponse({"error": "provider is required"}, status=400)
    if not api_key:
        return JsonResponse({"error": "api_key is required"}, status=400)

    key = UserApiKey.objects.create(
        user=request.user,
        provider=provider,
        name=name,
        api_key=api_key,
        is_active=True,
    )

    ensure_user_defaults(request.user)

    return JsonResponse(
        {
            "id": key.id,
            "provider": key.provider,
            "name": key.name,
            "is_active": key.is_active,
        },
        status=201,
    )


@require_POST
@api_login_required
def update_api_key(request, key_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    key = UserApiKey.objects.filter(user=request.user, id=key_id).first()
    if key is None:
        return JsonResponse({"error": "API key not found"}, status=404)

    name = data.get("name")
    api_key = data.get("api_key")

    update_fields: list[str] = []

    if name is not None:
        if not isinstance(name, str):
            return JsonResponse({"error": "name must be a string"}, status=400)
        key.name = name.strip()
        update_fields.append("name")

    if api_key is not None:
        if not isinstance(api_key, str):
            return JsonResponse({"error": "api_key must be a string"}, status=400)
        api_key = api_key.strip()
        if api_key:
            key.api_key = api_key
            update_fields.append("api_key")

    if update_fields:
        key.save(update_fields=[*update_fields, "updated_at"])

    return JsonResponse(
        {
            "id": key.id,
            "provider": key.provider,
            "name": key.name,
            "preview": _key_preview(key.api_key),
            "is_active": key.is_active,
        }
    )


@require_POST
@api_login_required
def set_api_key_active(request, key_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return JsonResponse({"error": "is_active must be a boolean"}, status=400)

    key = UserApiKey.objects.filter(user=request.user, id=key_id).first()
    if key is None:
        return JsonResponse({"error": "API key not found"}, status=404)

    if not is_active:
        has_active_models = UserModelConfig.objects.filter(
            user=request.user,
            api_key=key,
            is_active=True,
        ).exists()
        if has_active_models:
            return JsonResponse(
                {"error": "Cannot remove an API key used by an active model."},
                status=409,
            )

    key.is_active = is_active
    key.save(update_fields=["is_active", "updated_at"])

    return JsonResponse(
        {
            "id": key.id,
            "provider": key.provider,
            "name": key.name,
            "preview": _key_preview(key.api_key),
            "is_active": key.is_active,
        }
    )


@require_POST
@api_login_required
def add_database_connection(request):
    data, error = _parse_json_body(request)
    if error:
        return error

    name = (data.get("name", "") or "").strip()
    connection_string = (data.get("connection_string", "") or "").strip()
    memory = data.get("memory", "")
    if memory is None:
        memory = ""
    if not isinstance(memory, str):
        return JsonResponse({"error": "memory must be a string"}, status=400)

    if not name:
        return JsonResponse({"error": "name is required"}, status=400)
    if not connection_string:
        return JsonResponse({"error": "connection_string is required"}, status=400)

    try:
        db = UserDatabaseConnection.objects.create(
            user=request.user,
            name=name,
            connection_string=connection_string,
            memory=memory,
            is_active=True,
        )
    except IntegrityError:
        return JsonResponse(
            {"error": "A database connection with that name already exists."},
            status=409,
        )

    ensure_user_defaults(request.user)

    return JsonResponse(
        {
            "id": db.id,
            "name": db.name,
            "memory": db.memory or "",
            "is_active": db.is_active,
        },
        status=201,
    )


@require_POST
@api_login_required
def update_database_connection(request, connection_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    db = UserDatabaseConnection.objects.filter(
        user=request.user,
        id=connection_id,
    ).first()
    if db is None:
        return JsonResponse({"error": "Database connection not found"}, status=404)

    name = data.get("name")
    connection_string = data.get("connection_string")
    memory = data.get("memory")

    update_fields: list[str] = []

    if name is not None:
        if not isinstance(name, str):
            return JsonResponse({"error": "name must be a string"}, status=400)
        name = name.strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)
        db.name = name
        update_fields.append("name")

    if connection_string is not None:
        if not isinstance(connection_string, str):
            return JsonResponse(
                {"error": "connection_string must be a string"}, status=400
            )
        connection_string = connection_string.strip()
        if not connection_string:
            return JsonResponse(
                {"error": "connection_string is required"}, status=400
            )
        db.connection_string = connection_string
        update_fields.append("connection_string")

    if memory is not None:
        if not isinstance(memory, str):
            return JsonResponse({"error": "memory must be a string"}, status=400)
        db.memory = memory
        update_fields.append("memory")

    if update_fields:
        try:
            db.save(update_fields=[*update_fields, "updated_at"])
        except IntegrityError:
            return JsonResponse(
                {"error": "A database connection with that name already exists."},
                status=409,
            )

    return JsonResponse(
        {
            "id": db.id,
            "name": db.name,
            "memory": db.memory or "",
            "is_active": db.is_active,
        }
    )


@require_POST
@api_login_required
def set_database_connection_active(request, connection_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return JsonResponse({"error": "is_active must be a boolean"}, status=400)

    db = UserDatabaseConnection.objects.filter(
        user=request.user,
        id=connection_id,
    ).first()
    if db is None:
        return JsonResponse({"error": "Database connection not found"}, status=404)

    db.is_active = is_active
    db.save(update_fields=["is_active", "updated_at"])

    if not is_active:
        settings = get_or_create_user_settings(request.user)
        if settings.default_database_connection_id == db.id:
            settings.default_database_connection = None
            settings.save(update_fields=["default_database_connection", "updated_at"])

    ensure_user_defaults(request.user)

    return JsonResponse({"id": db.id, "name": db.name, "is_active": db.is_active})


@require_POST
@api_login_required
def add_model_config(request):
    data, error = _parse_json_body(request)
    if error:
        return error

    display_name = (data.get("display_name", "") or "").strip()
    model_name = (data.get("model_name", "") or "").strip()
    api_key_id = data.get("api_key_id")

    if not display_name:
        return JsonResponse({"error": "display_name is required"}, status=400)
    if not model_name:
        return JsonResponse({"error": "model_name is required"}, status=400)
    if not isinstance(api_key_id, int):
        return JsonResponse({"error": "api_key_id must be an integer"}, status=400)

    try:
        provider = parse_provider(model_name).lower()
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    api_key = UserApiKey.objects.filter(
        user=request.user,
        id=api_key_id,
        is_active=True,
    ).first()
    if api_key is None:
        return JsonResponse({"error": "API key not found"}, status=404)

    if api_key.provider.lower() != provider:
        return JsonResponse(
            {"error": "API key provider does not match model provider"},
            status=400,
        )

    try:
        model = UserModelConfig.objects.create(
            user=request.user,
            display_name=display_name,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            is_active=True,
        )
    except IntegrityError:
        return JsonResponse(
            {"error": "A model with that display name already exists."},
            status=409,
        )

    ensure_user_defaults(request.user)

    return JsonResponse(
        {
            "id": model.id,
            "display_name": model.display_name,
            "provider": model.provider,
            "model_name": model.model_name,
            "api_key_id": model.api_key_id,
            "is_active": model.is_active,
        },
        status=201,
    )


@require_POST
@api_login_required
def update_model_config(request, model_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    model = UserModelConfig.objects.filter(user=request.user, id=model_id).select_related(
        "api_key"
    ).first()
    if model is None:
        return JsonResponse({"error": "Model not found"}, status=404)

    display_name = data.get("display_name")
    model_name = data.get("model_name")
    api_key_id = data.get("api_key_id")

    update_fields: list[str] = []

    if display_name is not None:
        if not isinstance(display_name, str):
            return JsonResponse(
                {"error": "display_name must be a string"}, status=400
            )
        display_name = display_name.strip()
        if not display_name:
            return JsonResponse({"error": "display_name is required"}, status=400)
        model.display_name = display_name
        update_fields.append("display_name")

    if model_name is not None:
        if not isinstance(model_name, str):
            return JsonResponse({"error": "model_name must be a string"}, status=400)
        model_name = model_name.strip()
        if not model_name:
            return JsonResponse({"error": "model_name is required"}, status=400)
        try:
            provider = parse_provider(model_name).lower()
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        model.model_name = model_name
        model.provider = provider
        update_fields.extend(["model_name", "provider"])

    if api_key_id is not None:
        if not isinstance(api_key_id, int):
            return JsonResponse({"error": "api_key_id must be an integer"}, status=400)
        api_key = UserApiKey.objects.filter(
            user=request.user,
            id=api_key_id,
            is_active=True,
        ).first()
        if api_key is None:
            return JsonResponse({"error": "API key not found"}, status=404)

        provider_for_model = (
            model.provider
            if model_name is None
            else parse_provider(model.model_name).lower()
        )

        if api_key.provider.lower() != provider_for_model:
            return JsonResponse(
                {"error": "API key provider does not match model provider"},
                status=400,
            )

        model.api_key = api_key
        update_fields.append("api_key")

    if update_fields:
        try:
            model.save(update_fields=[*update_fields, "updated_at"])
        except IntegrityError:
            return JsonResponse(
                {"error": "A model with that display name already exists."},
                status=409,
            )

    return JsonResponse(
        {
            "id": model.id,
            "display_name": model.display_name,
            "provider": model.provider,
            "model_name": model.model_name,
            "api_key_id": model.api_key_id,
            "is_active": model.is_active,
        }
    )


@require_POST
@api_login_required
def set_model_config_active(request, model_id: int):
    data, error = _parse_json_body(request)
    if error:
        return error

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return JsonResponse({"error": "is_active must be a boolean"}, status=400)

    model = UserModelConfig.objects.filter(user=request.user, id=model_id).select_related(
        "api_key"
    ).first()
    if model is None:
        return JsonResponse({"error": "Model not found"}, status=404)

    if is_active and not model.api_key.is_active:
        return JsonResponse(
            {"error": "Cannot enable a model whose API key is inactive."},
            status=409,
        )

    model.is_active = is_active
    model.save(update_fields=["is_active", "updated_at"])

    if not is_active:
        settings = get_or_create_user_settings(request.user)
        if settings.default_model_config_id == model.id:
            settings.default_model_config = None
            settings.save(update_fields=["default_model_config", "updated_at"])

    ensure_user_defaults(request.user)

    return JsonResponse(
        {
            "id": model.id,
            "display_name": model.display_name,
            "provider": model.provider,
            "model_name": model.model_name,
            "api_key_id": model.api_key_id,
            "is_active": model.is_active,
        }
    )


@require_POST
@api_login_required
def update_user_settings(request):
    data, error = _parse_json_body(request)
    if error:
        return error

    settings = get_or_create_user_settings(request.user)

    default_db_id = data.get("default_database_connection_id")
    default_model_id = data.get("default_model_config_id")
    onboarding_completed = data.get("onboarding_completed")

    update_fields: list[str] = []

    if default_db_id is not None:
        if not isinstance(default_db_id, int):
            return JsonResponse(
                {"error": "default_database_connection_id must be an integer"},
                status=400,
            )
        db = UserDatabaseConnection.objects.filter(
            user=request.user,
            id=default_db_id,
            is_active=True,
        ).first()
        if db is None:
            return JsonResponse(
                {"error": "Database connection not found"}, status=404
            )
        settings.default_database_connection = db
        update_fields.append("default_database_connection")

    if default_model_id is not None:
        if not isinstance(default_model_id, int):
            return JsonResponse(
                {"error": "default_model_config_id must be an integer"},
                status=400,
            )
        model = UserModelConfig.objects.filter(
            user=request.user,
            id=default_model_id,
            is_active=True,
            api_key__is_active=True,
        ).first()
        if model is None:
            return JsonResponse({"error": "Model not found"}, status=404)
        settings.default_model_config = model
        update_fields.append("default_model_config")

    if onboarding_completed is not None:
        if not isinstance(onboarding_completed, bool):
            return JsonResponse(
                {"error": "onboarding_completed must be a boolean"}, status=400
            )

        if onboarding_completed:
            # Validate active defaults.
            status = compute_user_config_status(request.user)
            if not status.has_default_database:
                return JsonResponse(
                    {"error": "Select an active default database connection first"},
                    status=400,
                )
            if not status.has_default_model:
                return JsonResponse(
                    {"error": "Select an active default model first"},
                    status=400,
                )

        settings.onboarding_completed = onboarding_completed
        update_fields.append("onboarding_completed")

    if update_fields:
        settings.save(update_fields=[*update_fields, "updated_at"])

    ensure_user_defaults(request.user)
    status = compute_user_config_status(request.user)

    return JsonResponse(
        {
            "configured": status.is_configured,
            "onboarding_completed": status.onboarding_completed,
            "defaults": {
                "database_connection_id": settings.default_database_connection_id,
                "model_config_id": settings.default_model_config_id,
            },
        }
    )
