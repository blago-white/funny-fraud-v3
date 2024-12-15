import asyncio
import os
import dotenv

dotenv.load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers.callback.sessions import router as callback_router
from bot.handlers.message.sessions import router as sessions_router
from bot.handlers.message.gologin import router as gologin_router
from bot.handlers.message.sms import router as sms_router


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
                       sms_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
