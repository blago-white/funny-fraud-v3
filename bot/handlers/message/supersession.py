import asyncio

from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.inline import generate_sms_service_selection_kb
from bot.keyboards.reply import APPROVE_KB
from bot.states.forms import SuperSessionForm
from db.gologin import GologinApikeysRepository
from db.leads import LeadGenerationResultsService
from db.proxy import ProxyRepository
from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository)
from parser.main import LeadsGenerator
from .sessions import approve_session
from ..common import db_services_provider, leads_service_provider

router = Router(name=__name__)


@router.message(F.text == "🔱 Новая Cупер-Cессия")
@db_services_provider(provide_leads=False,
                      provide_elsms=True,
                      provide_smshub=True,
                      provide_helper=True,
                      provide_proxy=True)
async def make_super_session(
        message: Message,
        state: FSMContext,
        gologindb: GologinApikeysRepository,
        elsmsdb: ElSmsServiceApikeyRepository,
        smshubdb: SmsHubServiceApikeyRepository,
        helperdb: HelperSmsServiceApikeyRepository,
        proxydb: ProxyRepository):
    if not (gologindb.exists and (
            elsmsdb.exists or smshubdb.exists or helperdb.exists)):
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
                        reply_markup=APPROVE_KB)

    await message.reply(
        text=f"| Кол-во запросов: "
             f"{data.get("count_requests")}\n"
             f"| Реф. ссылки: <code>"
             f"{', '.join(data.get("ref_links"))}"
             f"</code>\n"
             f"| Макс. длительность: "
             f"{data.get("duration")} ч.\n",
        reply_markup=generate_sms_service_selection_kb(),
    )


@router.message(SuperSessionForm.approve_session)
@db_services_provider(provide_gologin=False)
@leads_service_provider
async def approve_super_session(
        message: Message, state: FSMContext,
        leadsdb: LeadGenerationResultsService,
        parser_service_class: LeadsGenerator
):
    if message.text != "✅ Запуск Супер Сессии!":
        await message.reply("✅ Отменено")
        await state.clear()
        return

    data = await state.get_data()

    total_count_requests = len(data.get("links")) * data.get("count_requests")

    for link in data.get("links"):
        await state.set_data({
            "ref_links": [link],
            "count_requests": min(10, int(data.get("count_requests"))),
            "timeout": float(data.get("duration")) / (total_count_requests / 10) * 60 * 60
        })

        await message.bot.send_message(
            chat_id=message.chat.id,
            text="⚠ <b>Скоро начнется автоматизированная "
                 "сессия в рамках Супер-Сессии</b>",
        )

        session = await approve_session(message=message, state=state)

        await message.bot.send_message(
            chat_id=message.chat.id,
            text="⚠ <b>Закончилась сессия в рамках Супер-Сессии</b>",
        )

        await state.clear()

        await asyncio.sleep(60)

    # current_session_form = dict(await state.get_data())

    # await message.reply(text="✅ Отлично, форма заполнена!\n",
    #                     reply_markup=APPROVE_KB)
    #
    # await message.reply(
    #     text=f"| Кол-во запросов: "
    #          f"{current_session_form.get("count_requests")}\n"
    #          f"| Реф. ссылки: <code>"
    #          f"{', '.join(current_session_form.get("ref_links"))}"
    #          f"</code>\n",
    #     reply_markup=generate_sms_service_selection_kb(),
    # )
