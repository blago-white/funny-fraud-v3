import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from .handlers import messages_router


async def main(token: str):
    bot = Bot(token=token, default=DefaultBotProperties(
        parse_mode="HTML"
    ))

    dp = Dispatcher(
        storage=RedisStorage.from_url(
            url="redis://localhost:6379/0"
        )
    )

    dp.include_router(router=messages_router)

    await dp.start_polling(bot)


async def startup():
    token = os.environ.get("TOKEN")

    await main(token)
