from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from inertia import render

from .models import UserApiKey, UserDatabaseConnection, UserModelConfig
from .services import (
    compute_user_config_status,
    ensure_user_defaults,
    get_or_create_user_settings,
    parse_json_body,
    parse_provider,
)
from .services.model_catalog import ALLOWED_MODEL_PROVIDERS, normalize_provider
from .services.serializers import (
    build_settings_props,
    build_thread_with_messages_props,
    build_threads_list_props,
    build_user_config_props,
)


@login_required
def home(request):
    return render(request, "Chat", props=build_user_config_props(request.user))


@login_required
def thread_list(request):
    """Render the threads list page."""
    return render(request, "ThreadList", props=build_threads_list_props(request.user))


@login_required
def thread_detail(request, thread_id: UUID):
    """Render a specific thread detail page."""
    thread_props = build_thread_with_messages_props(request.user, thread_id)
    if thread_props is None:
        raise Http404

    return render(
        request,
        "ThreadDetail",
        props={
            **thread_props,
            **build_user_config_props(request.user),
        },
    )


@login_required
def settings_page(request):
    return render(request, "Settings", props=build_settings_props(request.user))


def _settings_error(request, errors: dict):
    """Render Settings page with errors and 422 status."""
    return render(
        request,
        "Settings",
        props={**build_settings_props(request.user), "errors": errors},
        status=422,
    )


@login_required
@require_POST
def settings_add_db(request):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    name = (data.get("name", "") or "").strip()
    connection_string = (data.get("connection_string", "") or "").strip()
    memory = data.get("memory", "")
    if memory is None:
        memory = ""
    if not isinstance(memory, str):
        return _settings_error(request, {"memory": "memory must be a string"})

    if not name:
        return _settings_error(request, {"name": "name is required"})
    if not connection_string:
        return _settings_error(
            request, {"connection_string": "connection_string is required"}
        )

    try:
        UserDatabaseConnection.objects.create(
            user=request.user,
            name=name,
            connection_string=connection_string,
            memory=memory,
            is_active=True,
        )
    except IntegrityError:
        return _settings_error(
            request, {"name": "A database connection with that name already exists."}
        )

    ensure_user_defaults(request.user)
    return redirect("settings")


@login_required
@require_POST
def settings_update_db(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    db = UserDatabaseConnection.objects.filter(user=request.user, id=pk).first()
    if db is None:
        return _settings_error(request, {"form": "Database connection not found"})

    name = data.get("name")
    connection_string = data.get("connection_string")
    memory = data.get("memory")

    update_fields: list[str] = []

    if name is not None:
        if not isinstance(name, str):
            return _settings_error(request, {"name": "name must be a string"})
        name = name.strip()
        if not name:
            return _settings_error(request, {"name": "name is required"})
        db.name = name
        update_fields.append("name")

    if connection_string is not None:
        if not isinstance(connection_string, str):
            return _settings_error(
                request, {"connection_string": "connection_string must be a string"}
            )
        connection_string = connection_string.strip()
        if not connection_string:
            return _settings_error(
                request, {"connection_string": "connection_string is required"}
            )
        db.connection_string = connection_string
        update_fields.append("connection_string")

    if memory is not None:
        if not isinstance(memory, str):
            return _settings_error(request, {"memory": "memory must be a string"})
        db.memory = memory
        update_fields.append("memory")

    if update_fields:
        try:
            db.save(update_fields=[*update_fields, "updated_at"])
        except IntegrityError:
            return _settings_error(
                request,
                {"name": "A database connection with that name already exists."},
            )

    return redirect("settings")


@login_required
@require_POST
def settings_set_db_active(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return _settings_error(request, {"is_active": "is_active must be a boolean"})

    db = UserDatabaseConnection.objects.filter(user=request.user, id=pk).first()
    if db is None:
        return _settings_error(request, {"form": "Database connection not found"})

    db.is_active = is_active
    db.save(update_fields=["is_active", "updated_at"])

    if not is_active:
        settings = get_or_create_user_settings(request.user)
        if settings.default_database_connection_id == db.id:
            settings.default_database_connection = None
            settings.save(update_fields=["default_database_connection", "updated_at"])

    ensure_user_defaults(request.user)
    return redirect("settings")


@login_required
@require_POST
def settings_add_api_key(request):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    provider_raw = data.get("provider")
    if not isinstance(provider_raw, str):
        return _settings_error(request, {"provider": "provider must be a string"})
    provider = normalize_provider(provider_raw)

    name = data.get("name")
    if name is None:
        name = ""
    if not isinstance(name, str):
        return _settings_error(request, {"name": "name must be a string"})
    name = name.strip()

    api_key = data.get("api_key")
    if api_key is None:
        api_key = ""
    if not isinstance(api_key, str):
        return _settings_error(request, {"api_key": "api_key must be a string"})
    api_key = api_key.strip()

    if not provider:
        return _settings_error(request, {"provider": "provider is required"})
    if provider not in ALLOWED_MODEL_PROVIDERS:
        return _settings_error(
            request,
            {"provider": "provider must be one of: anthropic, openai, google"},
        )
    if not api_key:
        return _settings_error(request, {"api_key": "api_key is required"})

    UserApiKey.objects.create(
        user=request.user,
        provider=provider,
        name=name,
        api_key=api_key,
        is_active=True,
    )

    ensure_user_defaults(request.user)
    return redirect("settings")


@login_required
@require_POST
def settings_update_api_key(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    key = UserApiKey.objects.filter(user=request.user, id=pk).first()
    if key is None:
        return _settings_error(request, {"form": "API key not found"})

    name = data.get("name")
    api_key = data.get("api_key")

    update_fields: list[str] = []

    if name is not None:
        if not isinstance(name, str):
            return _settings_error(request, {"name": "name must be a string"})
        key.name = name.strip()
        update_fields.append("name")

    if api_key is not None:
        if not isinstance(api_key, str):
            return _settings_error(request, {"api_key": "api_key must be a string"})
        api_key = api_key.strip()
        if api_key:
            key.api_key = api_key
            update_fields.append("api_key")

    if update_fields:
        key.save(update_fields=[*update_fields, "updated_at"])

    return redirect("settings")


@login_required
@require_POST
def settings_set_api_key_active(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return _settings_error(request, {"is_active": "is_active must be a boolean"})

    key = UserApiKey.objects.filter(user=request.user, id=pk).first()
    if key is None:
        return _settings_error(request, {"form": "API key not found"})

    if not is_active:
        has_active_models = UserModelConfig.objects.filter(
            user=request.user,
            api_key=key,
            is_active=True,
        ).exists()
        if has_active_models:
            return _settings_error(
                request,
                {"form": "Cannot remove an API key used by an active model."},
            )

    key.is_active = is_active
    key.save(update_fields=["is_active", "updated_at"])

    return redirect("settings")


@login_required
@require_POST
def settings_add_model(request):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    display_name = (data.get("display_name", "") or "").strip()
    model_name = (data.get("model_name", "") or "").strip()
    api_key_id = data.get("api_key_id")

    if not display_name:
        return _settings_error(request, {"display_name": "display_name is required"})
    if not model_name:
        return _settings_error(request, {"model_name": "model_name is required"})
    if not isinstance(api_key_id, int):
        return _settings_error(request, {"api_key_id": "api_key_id must be an integer"})

    try:
        provider = parse_provider(model_name).lower()
    except ValueError as e:
        return _settings_error(request, {"model_name": str(e)})

    if provider not in ALLOWED_MODEL_PROVIDERS:
        return _settings_error(
            request,
            {"model_name": "Only Anthropic, OpenAI, and Google models are supported."},
        )

    api_key = UserApiKey.objects.filter(
        user=request.user,
        id=api_key_id,
        is_active=True,
    ).first()
    if api_key is None:
        return _settings_error(request, {"api_key_id": "API key not found"})

    if api_key.provider.lower() != provider:
        return _settings_error(
            request,
            {"api_key_id": "API key provider does not match model provider"},
        )

    try:
        UserModelConfig.objects.create(
            user=request.user,
            display_name=display_name,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            is_active=True,
        )
    except IntegrityError:
        return _settings_error(
            request,
            {"display_name": "A model with that display name already exists."},
        )

    ensure_user_defaults(request.user)
    return redirect("settings")


@login_required
@require_POST
def settings_update_model(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    model = (
        UserModelConfig.objects.filter(user=request.user, id=pk)
        .select_related("api_key")
        .first()
    )
    if model is None:
        return _settings_error(request, {"form": "Model not found"})

    display_name = data.get("display_name")
    model_name = data.get("model_name")
    api_key_id = data.get("api_key_id")

    update_fields: list[str] = []

    if display_name is not None:
        if not isinstance(display_name, str):
            return _settings_error(
                request, {"display_name": "display_name must be a string"}
            )
        display_name = display_name.strip()
        if not display_name:
            return _settings_error(
                request, {"display_name": "display_name is required"}
            )
        model.display_name = display_name
        update_fields.append("display_name")

    if model_name is not None:
        if not isinstance(model_name, str):
            return _settings_error(
                request, {"model_name": "model_name must be a string"}
            )
        model_name = model_name.strip()
        if not model_name:
            return _settings_error(request, {"model_name": "model_name is required"})
        try:
            provider = parse_provider(model_name).lower()
        except ValueError as e:
            return _settings_error(request, {"model_name": str(e)})

        if provider not in ALLOWED_MODEL_PROVIDERS:
            return _settings_error(
                request,
                {
                    "model_name": "Only Anthropic, OpenAI, and Google models are supported."
                },
            )

        model.model_name = model_name
        model.provider = provider
        update_fields.extend(["model_name", "provider"])

    if api_key_id is not None:
        if not isinstance(api_key_id, int):
            return _settings_error(
                request, {"api_key_id": "api_key_id must be an integer"}
            )
        api_key = UserApiKey.objects.filter(
            user=request.user,
            id=api_key_id,
            is_active=True,
        ).first()
        if api_key is None:
            return _settings_error(request, {"api_key_id": "API key not found"})

        provider_for_model = (
            model.provider
            if model_name is None
            else parse_provider(model.model_name).lower()
        )

        if api_key.provider.lower() != provider_for_model:
            return _settings_error(
                request,
                {"api_key_id": "API key provider does not match model provider"},
            )

        model.api_key = api_key
        update_fields.append("api_key")

    if update_fields:
        try:
            model.save(update_fields=[*update_fields, "updated_at"])
        except IntegrityError:
            return _settings_error(
                request,
                {"display_name": "A model with that display name already exists."},
            )

    return redirect("settings")


@login_required
@require_POST
def settings_set_model_active(request, pk: int):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    is_active = data.get("is_active")
    if not isinstance(is_active, bool):
        return _settings_error(request, {"is_active": "is_active must be a boolean"})

    model = (
        UserModelConfig.objects.filter(user=request.user, id=pk)
        .select_related("api_key")
        .first()
    )
    if model is None:
        return _settings_error(request, {"form": "Model not found"})

    if is_active and not model.api_key.is_active:
        return _settings_error(
            request,
            {"form": "Cannot enable a model whose API key is inactive."},
        )

    model.is_active = is_active
    model.save(update_fields=["is_active", "updated_at"])

    if not is_active:
        settings = get_or_create_user_settings(request.user)
        if settings.default_model_config_id == model.id:
            settings.default_model_config = None
            settings.save(update_fields=["default_model_config", "updated_at"])

    ensure_user_defaults(request.user)
    return redirect("settings")


@login_required
@require_POST
def settings_update_config(request):
    data, error = parse_json_body(request)
    if error:
        return _settings_error(request, {"form": "Invalid JSON"})

    settings = get_or_create_user_settings(request.user)

    default_db_id = data.get("default_database_connection_id")
    default_model_id = data.get("default_model_config_id")
    onboarding_completed = data.get("onboarding_completed")

    update_fields: list[str] = []

    if default_db_id is not None:
        if not isinstance(default_db_id, int):
            return _settings_error(
                request,
                {"default_database_connection_id": "must be an integer"},
            )
        db = UserDatabaseConnection.objects.filter(
            user=request.user,
            id=default_db_id,
            is_active=True,
        ).first()
        if db is None:
            return _settings_error(
                request,
                {"default_database_connection_id": "Database connection not found"},
            )
        settings.default_database_connection = db
        update_fields.append("default_database_connection")

    if default_model_id is not None:
        if not isinstance(default_model_id, int):
            return _settings_error(
                request,
                {"default_model_config_id": "must be an integer"},
            )
        model = UserModelConfig.objects.filter(
            user=request.user,
            id=default_model_id,
            is_active=True,
            api_key__is_active=True,
        ).first()
        if model is None:
            return _settings_error(
                request,
                {"default_model_config_id": "Model not found"},
            )
        settings.default_model_config = model
        update_fields.append("default_model_config")

    if onboarding_completed is not None:
        if not isinstance(onboarding_completed, bool):
            return _settings_error(
                request,
                {"onboarding_completed": "must be a boolean"},
            )

        if onboarding_completed:
            status = compute_user_config_status(request.user)
            if not status.has_default_database:
                return _settings_error(
                    request,
                    {
                        "onboarding_completed": "Select an active default database connection first"
                    },
                )
            if not status.has_default_model:
                return _settings_error(
                    request,
                    {"onboarding_completed": "Select an active default model first"},
                )

        settings.onboarding_completed = onboarding_completed
        update_fields.append("onboarding_completed")

    if update_fields:
        settings.save(update_fields=[*update_fields, "updated_at"])

    ensure_user_defaults(request.user)
    return redirect("settings")
