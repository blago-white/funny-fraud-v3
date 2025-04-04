from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ._labels import STATISTICS_MESSAGE
from db.statistics import LeadsGenerationStatisticsService
from ..common import db_services_provider

router = Router(name=__name__)


@router.message(Command("stats"))
@db_services_provider(provide_leads=False, provide_gologin=False,
                      provide_stats=True)
async def show_statistics(
        message: Message,
        statsdb: LeadsGenerationStatisticsService):
    today_data, total = statsdb.get_today_leads_count()

    sms_balance_delta = statsdb.get_today_sms_delta_balance()

    print(today_data, total)

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=STATISTICS_MESSAGE.format(
            total=total,
            links=("\n".join([
                 f"{link} | <b>+{today_data[link]}</b>"
                 for link in today_data
            ]) + "\n") if today_data else "",
            balance_delta=sms_balance_delta,
            avg_price=abs(sms_balance_delta / total) if total and sms_balance_delta else 0
        )
    )
