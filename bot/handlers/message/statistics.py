from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.statistics import LeadsGenerationStatisticsService
from ..common import db_services_provider

router = Router(name=__name__)


@router.message(Command("stats"))
@db_services_provider(provide_leads=False, provide_gologin=False, provide_stats=True)
async def show_statistics(
        message: Message,
        statsdb: LeadsGenerationStatisticsService):
    today_data, total = statsdb.get_today()

    print(today_data, total)

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"<b>Статистика лидов за cегодня [{total} Лидов]:</b>\n\n" +
             "\n".join([
                 f"{link} | <b>+{today_data[link]}</b>"
                 for link in today_data
             ])
    )
