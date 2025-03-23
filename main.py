import asyncio
import os
import dotenv

dotenv.load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers.callback.sms import router as sms_callback_router
from bot.handlers.callback.sessions import router as callback_router
from bot.handlers.callback.supervisor import router as supervisor_router

from bot.handlers.message.sessions import router as sessions_router
from bot.handlers.message.gologin import router as gologin_router
from bot.handlers.message.proxy import router as proxy_router
from bot.handlers.message.sms import router as sms_router
from bot.handlers.message.statistics import router as statistics_router
from bot.handlers.message.supersession import router as ss_router

from server import start_server_pooling


async def main():
    dp = Dispatcher()

    bot = Bot(
        token=os.environ.get("BOT_TOKEN"),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp.include_routers(callback_router,
                       sessions_router,
                       gologin_router,
                       sms_router,
                       proxy_router,
                       sms_callback_router,
                       statistics_router,
                       ss_router,
                       supervisor_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    start_server_pooling()
    asyncio.run(main())
