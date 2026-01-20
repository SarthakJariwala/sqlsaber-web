from functools import singledispatchmethod
from uuid import UUID

from pydantic_ai.messages import (
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
)

from .models import Message


class DatabaseStreamingHandler:
    def __init__(self, thread_id: UUID | str):
        self.thread_id = thread_id
        self._buffer: str = ""
        self._current_kind: type[TextPart] | type[ThinkingPart] | None = None

    async def handle_event_stream(self, event_stream):
        async for event in event_stream:
            await self.on_event(event)

    @singledispatchmethod
    async def on_event(self, event: AgentStreamEvent) -> None:
        pass

    @on_event.register
    async def on_part_start(self, event: PartStartEvent) -> None:
        part = event.part
        if isinstance(part, TextPart | ThinkingPart):
            if self._current_kind is not None and self._current_kind != type(part):
                await self.flush_buffer()
            self._current_kind = type(part)
            if part.content:
                self._buffer += part.content

    @on_event.register
    async def on_part_delta(self, event: PartDeltaEvent) -> None:
        delta = event.delta
        if isinstance(delta, TextPartDelta | ThinkingPartDelta):
            content_delta = delta.content_delta or ""
            if content_delta:
                self._buffer += content_delta

    @on_event.register
    async def on_part_end(self, event: PartEndEvent) -> None:
        await self.flush_buffer()

    @on_event.register
    async def on_tool_call(self, event: FunctionToolCallEvent) -> None:
        await self.flush_buffer()
        await self._save_message(
            message_type=Message.Type.TOOL_CALL,
            content={
                "tool_name": event.part.tool_name,
                "tool_args": event.part.args,
            },
        )

    @on_event.register
    async def on_tool_result(self, event: FunctionToolResultEvent) -> None:
        await self._save_message(
            message_type=Message.Type.TOOL_RESULT,
            content={
                "tool_name": event.result.tool_name,
                "result": event.result.content,
            },
        )

    async def flush_buffer(self) -> None:
        if not self._buffer or self._current_kind is None:
            return

        message_type = (
            Message.Type.THINKING
            if self._current_kind == ThinkingPart
            else Message.Type.ASSISTANT
        )

        await self._save_message(
            message_type=message_type,
            content={"text": self._buffer},
        )

        self._buffer = ""
        self._current_kind = None

    async def _save_message(self, message_type: str, content: dict) -> None:
        await Message.objects.acreate(
            thread_id=self.thread_id,
            type=message_type,
            content=content,
        )
