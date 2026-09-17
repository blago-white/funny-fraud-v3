import asyncio

from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.inline import get_session_presets_kb, \
    get_supersession_canceling_kb
from bot.keyboards.reply import SS_APPROVE_KB
from bot.states.forms import SuperSessionForm
from db.gologin import GologinApikeysRepository
from db.proxy import ProxyRepository
from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository,
                    CodexSmsServiceApikeyRepository)
from db.statistics import LeadsGenerationStatisticsService
from .sessions import approve_session
from ..common import db_services_provider

router = Router(name=__name__)


@router.message(F.text == "🔱 Новая Cупер-Cессия")
@db_services_provider(provide_leads=False,
                      provide_elsms=True,
                      provide_smshub=True,
                      provide_helper=True,
                      provide_codexsms=True,
                      provide_proxy=True)
async def make_super_session(
        message: Message,
        state: FSMContext,
        gologindb: GologinApikeysRepository,
        elsmsdb: ElSmsServiceApikeyRepository,
        smshubdb: SmsHubServiceApikeyRepository,
        helperdb: HelperSmsServiceApikeyRepository,
        codexsmsdb: CodexSmsServiceApikeyRepository,
        proxydb: ProxyRepository):
    if not (gologindb.exists and (
            elsmsdb.exists or
            smshubdb.exists or
            helperdb.exists or
            codexsmsdb.exists)):
        return await message.reply(
            "⭕Сначала добавьте <b>Gologin apikey</b> и один из"
            "<b>Sms-Service apikey</b>"
        )

    can_use_proxy, proxy = proxydb.can_use

    if not can_use_proxy:
        return await message.reply(
            f"⭕Обновите прокси! <code>[{proxy}]</code>"
        )

    await state.set_state(state=SuperSessionForm.set_count_complete_requests)

    await message.reply(
        text="Какое финальное колличество полных заявок "
             "на каждую ссылку суперсессии?",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(SuperSessionForm.set_count_complete_requests)
async def set_count_requests(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply(text="Неверное значение\n\n<i>должно быть "
                                 "целым числом</i>")
        return

    count = abs(int(message.text))

    await state.set_data(data={"count_requests": count})
    await state.set_state(SuperSessionForm.set_ref_link)

    await message.reply(
        text="<b>Отлично</b>, теперь реф. ссылки:"
    )


@router.message(SuperSessionForm.set_ref_link)
async def process_ref_link(message: Message, state: FSMContext):
    ref_links = message.text.split("\n")

    for link in ref_links:
        if (not link.startswith("https://")) or (" " in link):
            await message.reply("Неверный формат\n\n<i>нужна ссылка</i>")
            return

    current_session_form = dict(await state.get_data())
    await state.set_data(data=current_session_form | {
        "ref_links": ref_links
    })

    await state.set_state(state=SuperSessionForm.set_card_number)

    await message.reply(text="🔢Введите данные карты:\n\n"
                             "<i>number@date@cvc</i>")


@router.message(SuperSessionForm.set_card_number)
async def set_payments_card(message: Message, state: FSMContext):
    if not len(message.text.split("@")) == 3:
        return await message.reply(
            text="Неверный формат, пример:\n<i>1111222233334444@12.24@999</i>"
        )

    await state.set_data(
        data=dict(await state.get_data()) | {
            "payments_card": message.text.replace(" ", "")
        }
    )

    data = dict(await state.get_data())

    await message.reply(
        text="Теперь укажите макс. длительность суперсессии в часах\n\n"
             f"Рекомендуется: {(len(data.get("ref_links")) * data.get("count_requests") / 10) * 30 / 60} ч."
    )

    await state.set_state(state=SuperSessionForm.set_duration)


@router.message(SuperSessionForm.set_duration)
async def set_duration(message: Message, state: FSMContext):
    try:
        duration = float(message.text)
    except:
        return await message.reply("Неверное значение")

    data = dict(await state.get_data())

    await state.set_data(data=data | {"duration": duration})

    await state.set_state(state=SuperSessionForm.approve_session)

    await message.reply(text="✅ Отлично, форма заполнена!\n",
                        reply_markup=SS_APPROVE_KB)

    await message.reply(
        text=f"| Кол-во запросов: "
             f"{data.get("count_requests")}\n"
             f"| Реф. ссылки: <code>"
             f"{', '.join(data.get("ref_links"))}"
             f"</code>\n"
             f"| Макс. длительность: "
             f"{duration} ч.\n",
        reply_markup=get_session_presets_kb(),
    )


@router.message(SuperSessionForm.approve_session)
async def approve_super_session(
        message: Message, state: FSMContext,
):
    if message.text != "✅Начать сеанс":
        await message.reply("✅ Отменено")
        await state.clear()
        return

    async def _process_cooldown():
        try:
            delta_balance = (
                    session_call_stack.default_sms_service_balance -
                    session_call_stack.sms_service.balance
            )
        except:
            delta_balance = 0

        if delta_balance >= (1.35 * current_session_count_requests * 9):
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="▶ <b>Пауза на 10 мин. из-за высоких трат! [1]</b>"
            )
            await asyncio.sleep(60 * 10)

        if delta_balance >= (1.5 * current_session_count_requests * 9):
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="▶ <b>Пауза на 10 мин. из-за высоких трат! [2]</b>"
            )
            await asyncio.sleep(60 * 10)

    async def _reduce_leads_gap(before_stats: dict, target_count_leads: int):
        post_session_links = []

        for target_link in before_stats:
            count_leads_of_link = before_stats[target_link]
            leads_delta = target_count_leads - count_leads_of_link

            if count_leads_of_link < target_count_leads and (leads_delta > 5):
                post_session_links.append((target_link, leads_delta))

        if not post_session_links:
            return

        for target_link, delta in post_session_links:
            await state.set_data({
                "ref_links": [target_link],
                "count_requests": min(delta+5, 30),
                "payments_card": data.get("payments_card"),
                "timeout": min(max(delta*3, 15), 60) * 60,
                "sms-service": data.get("sms-service"),
                "supervised": data.get("supervised")
            })

            await message.bot.send_message(
                chat_id=message.chat.id,
                text="⚠ <b>Скоро начнется автоматизированная "
                     "пост-сессия в рамках Супер-Сессии</b>",
                reply_markup=get_supersession_canceling_kb()
            )

            after_post_session_data, _ = await approve_session(
                message=message, state=state
            )

            await message.bot.send_message(
                chat_id=message.chat.id,
                text="⚠ <b>Закончилась пост-сессия в рамках Супер-Сессии</b>",
            )

            await _process_cooldown()

            await _process_session_shotdown(
                after_session_data=after_post_session_data,
                message=message
            )

    data = await state.get_data()

    total_count_requests = len(data.get("ref_links")) * data.get(
        "count_requests"
    )

    links_stats_before, _ = LeadsGenerationStatisticsService().get_today_leads_count()

    for link in data.get("ref_links"):
        link_count_requests = int(data.get("count_requests"))

        while link_count_requests > 0:
            current_session_count_requests = min(20, link_count_requests)

            link_count_requests -= current_session_count_requests

            await state.set_data({
                "ref_links": [link],
                "count_requests": current_session_count_requests,
                "payments_card": data.get("payments_card"),
                "timeout": float(data.get("duration")) / (
                        total_count_requests / 10) * 60 * 60,
                "sms-service": data.get("sms-service"),
                "supervised": data.get("supervised")
            })

            await message.bot.send_message(
                chat_id=message.chat.id,
                text="⚠ <b>Скоро начнется автоматизированная "
                     "сессия в рамках Супер-Сессии</b>",
                reply_markup=get_supersession_canceling_kb()
            )

            after_session_data, session_call_stack = await approve_session(
                message=message, state=state
            )

            await message.bot.send_message(
                chat_id=message.chat.id,
                text="⚠ <b>Закончилась сессия в рамках Супер-Сессии</b>",
            )

            await _process_cooldown()

            await _process_session_shotdown(
                after_session_data=after_session_data,
                message=message
            )

            await asyncio.sleep(5)

    if data.get("use-strict"):
        await message.bot.send_message(chat_id=message.chat.id,
                                       text="✅ Начата добивка колличества лидов!")

        await _reduce_leads_gap(
            before_stats=links_stats_before,
            target_count_leads=int(data.get("count_requests"))
        )

    await message.bot.send_message(chat_id=message.chat.id,
                                   text="✅ Супер-Сессия завершена!")


async def _process_session_shotdown(after_session_data: dict, message: Message):
    if after_session_data.get("stop-supersession"):
        return await message.bot.send_message(
            chat_id=message.chat.id,
            text="<b>🚫 Суперсессия прервана</b>"
        )
