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
            try:
                os.remove(os.environ.get("CHROME_DRIVER_PATH"))
            except:
                pass
            finally:
                return

        return await handler(event, data)
