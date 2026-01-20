from uuid import UUID

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Message, Thread
from .services import (
    api_login_required,
    get_selected_or_default_db,
    get_selected_or_default_model,
    get_thread_for_user,
    parse_json_body,
    serialize_thread,
    serialize_thread_summary,
    threads_queryset_for_user,
)
from .tasks import run_sqlsaber_query


@api_login_required
def threads_api(request):
    """Handle GET (list threads) and POST (create thread) on /api/threads/."""
    if request.method == "GET":
        threads = threads_queryset_for_user(request.user).order_by("-updated_at")
        return JsonResponse({"threads": [serialize_thread_summary(t) for t in threads]})
    if request.method == "POST":
        return create_thread(request)
    return JsonResponse({"error": "Method not allowed"}, status=405)


def create_thread(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    data, error = parse_json_body(request)
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
        return JsonResponse({"error": "model_config_id must be an integer"}, status=400)

    db = get_selected_or_default_db(
        request.user,
        selected_id=database_connection_id,
    )
    model = get_selected_or_default_model(
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

    run_sqlsaber_query.defer(thread_id=str(thread.id), prompt=prompt)

    return JsonResponse({"id": str(thread.id)})


@require_GET
@api_login_required
def get_messages(request, thread_id: UUID):
    thread = get_thread_for_user(request.user, thread_id)
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
    )


@require_POST
@api_login_required
def continue_thread(request, thread_id: UUID):
    """Continue an existing thread with a follow-up message."""
    data, error = parse_json_body(request)
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
        return JsonResponse({"error": "model_config_id must be an integer"}, status=400)

    thread = get_thread_for_user(request.user, thread_id)
    if thread is None:
        return JsonResponse({"error": "Thread not found"}, status=404)

    if thread.status == Thread.Status.RUNNING:
        return JsonResponse(
            {"error": "Thread is currently running. Please wait for completion."},
            status=409,
        )
    if thread.status == Thread.Status.PENDING:
        return JsonResponse({"error": "Thread has not started yet."}, status=409)

    db = get_selected_or_default_db(
        request.user,
        selected_id=database_connection_id,
    )
    model = get_selected_or_default_model(
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
        thread_id=str(thread.id),
        prompt=prompt,
        message_history=thread.content,
    )

    return JsonResponse({"id": thread.id, "status": "queued"})
