from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Any

from quotas.main import QuotasManager


class QuotasMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        if not QuotasManager().validate_quota:
            return

        return await handler(event, data)
