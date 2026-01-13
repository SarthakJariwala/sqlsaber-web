from collections.abc import AsyncIterable

import pydantic
from asgiref.sync import sync_to_async
from procrastinate.contrib.django import app
from pydantic_ai import RunContext
from pydantic_ai.messages import AgentStreamEvent, ModelMessage
from pydantic_core import to_jsonable_python
from sqlsaber import SQLSaber

from .models import Thread
from .services import get_runtime_config_for_thread_id
from .streaming import DatabaseStreamingHandler

# TypeAdapter for deserializing message history from JSON
_MessageHistoryAdapter = pydantic.TypeAdapter(list[ModelMessage])


@app.task(queue="sqlsaber")
async def run_sqlsaber_query(
    thread_id: int,
    prompt: str,
    message_history: list[dict] | None = None,
) -> None:
    try:
        await Thread.objects.filter(pk=thread_id).aupdate(status=Thread.Status.RUNNING)

        handler = DatabaseStreamingHandler(thread_id=thread_id)

        parsed_history = None
        if message_history:
            parsed_history = _MessageHistoryAdapter.validate_python(message_history)

        runtime_config = await sync_to_async(
            get_runtime_config_for_thread_id,
            thread_sensitive=True,
        )(thread_id)

        if not runtime_config.database_connection:
            raise RuntimeError("Database connection is empty. Update it in /settings.")

        async with SQLSaber(
            database=runtime_config.database_connection,
            thinking=True,
            api_key=runtime_config.api_key,
            model_name=runtime_config.model_name,
            memory=runtime_config.memory,
        ) as saber:

            async def event_stream_handler(
                ctx: RunContext,
                event_stream: AsyncIterable[AgentStreamEvent],
            ):
                await handler.handle_event_stream(event_stream)

            result = await saber.query(
                prompt,
                message_history=parsed_history,
                event_stream_handler=event_stream_handler,
            )

        await handler.flush_buffer()
        await Thread.objects.filter(pk=thread_id).aupdate(
            status=Thread.Status.COMPLETED,
            content=to_jsonable_python(result.all_messages),
            error_message="",  # Clear any previous error
        )
    except Exception as e:
        await Thread.objects.filter(pk=thread_id).aupdate(
            status=Thread.Status.ERROR,
            error_message=str(e)[:1000],
        )
