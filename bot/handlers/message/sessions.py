import asyncio
import time

from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.inline import generate_leads_statuses_kb
from bot.keyboards.reply import APPROVE_KB, EMPTY_KB
from bot.keyboards.reply import MAIN_MENU_KB
from bot.states.forms import SessionForm, PaymentCodeSettingForm
from db.leads import LeadGenerationResultsService
from db.gologin import GologinApikeysRepository
from db.transfer import LeadGenResultStatus
from db.sms import SmsServiceApikeyRepository
from db.proxy import ProxyRepository
from parser.profiles.gologin import GologinProfilesManager
from parser.sessions import LeadsGenerationSession
from parser.main import LeadsGenerator
from ..common import db_services_provider, leads_service_provider

from ._utils import all_threads_ended, leads_differences_exists
from . import _labels as labels

router = Router(name=__name__)


@router.message(CommandStart())
@db_services_provider(provide_leads=False,
                      provide_sms=True,
                      provide_proxy=True)
async def start(
        message: Message, state: FSMContext,
        gologindb: GologinApikeysRepository,
        smsdb: SmsServiceApikeyRepository,
        proxydb: ProxyRepository):
    await state.clear()

    gologin_apikey, sms_service_apikey = (
        gologindb.get_current(), smsdb.get_current()
    )

    proxy_ok, _ = proxydb.can_use

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"🏠<b>Меню Парсера</b>\n"
             f"🤖<b>Gologin apikey: {"✅" if gologin_apikey else "📛"}"
             f"<code>{gologin_apikey[:6] + '...' + gologin_apikey[-3:]
                      if gologin_apikey
                      else ""}"
             f"</code></b>\n"
             f"☎<b>El-Sms apikey: {"✅" if sms_service_apikey else "📛"}"
             f"<code>{sms_service_apikey[:6] + '...' + sms_service_apikey[-3:]
                      if sms_service_apikey
                      else ""}"
             f"</code></b>\n"
             f"🔐<b>Proxy: {"✅" if proxy_ok else "📛"}</b>",
        reply_markup=MAIN_MENU_KB
    )


@router.message(F.text == "🔥Новый Сеанс")
@db_services_provider(provide_leads=False,
                      provide_sms=True,
                      provide_proxy=True)
async def new_session(
        message: Message,
        state: FSMContext,
        gologindb: GologinApikeysRepository,
        smsdb: SmsServiceApikeyRepository,
        proxydb: ProxyRepository):
    if not (gologindb.exists and smsdb.exists):
        return await message.reply(
            "⭕Сначала добавьте <b>Gologin apikey</b> и "
            "<b>El-Sms apikey</b>"
        )

    can_use_proxy, proxy = proxydb.can_use

    if not can_use_proxy:
        return await message.reply(
            f"⭕Обновите прокси! <code>[{proxy}]</code>"
        )

    await state.set_state(state=SessionForm.set_count_complete_requests)

    await message.reply(
        text="Какое колличество полных заявок"
             "\n\n<i>во время тестирования игнорируется</i>",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(SessionForm.set_count_complete_requests)
async def set_count_requests(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply(text="Неверное значение\n\n<i>должно быть "
                                 "целым числом</i>")
        return

    count = abs(int(message.text))

    await state.set_data(data={"count_requests": count})
    await state.set_state(SessionForm.set_ref_link)

    await message.reply(
        text="<b>Отлично</b>, теперь реф. ссылка:"
    )


@router.message(SessionForm.set_ref_link)
async def process_ref_link(message: Message, state: FSMContext):
    ref_link = message.text

    if (not ref_link.startswith("https://")) or (" " in ref_link):
        await message.reply("Неверный формат\n\n<i>нужна ссылка</i>")
        return

    current_session_form = dict(await state.get_data())
    await state.set_data(data=current_session_form | {"ref_link": ref_link})

    await state.set_state(state=SessionForm.set_card_number)

    await message.reply(text="🔢Введите данные карты:\n\n"
                             "<i>number@date@cvc</i>")


@router.message(SessionForm.set_card_number)
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

    await state.set_state(state=SessionForm.approve_session)

    current_session_form = dict(await state.get_data())

    await message.reply(
        text="✅ Отлично, форма заполнена!\n"
             f"| Кол-во запросов: "
             f"{current_session_form.get("count_requests")}\n"
             f"| Реф. ссылка: <code>"
             f"{current_session_form.get("ref_link")}</code>\n",
        reply_markup=APPROVE_KB,
    )


@router.message(SessionForm.approve_session)
@db_services_provider(provide_gologin=False)
@leads_service_provider
async def approve_session(
        message: Message, state: FSMContext,
        leadsdb: LeadGenerationResultsService,
        parser_service: LeadsGenerator
):
    if message.text != "✅Начать сеанс":
        await message.reply("✅Отменен")
        await state.clear()
        return

    session_form = await state.get_data()

    session_form = LeadsGenerationSession(
        ref_link=session_form.get("ref_link"),
        card=session_form.get("payments_card"),
        count=session_form.get("count_requests"),
    )

    await state.clear()

    replyed = await message.reply(
        text=labels.SESSION_INFO,
        reply_markup=EMPTY_KB
    )

    session_id = parser_service.mass_generate(data=session_form)

    leads, prev_leads, START_POLLING = None, list(), time.time()

    while True:
        leads = leadsdb.get(session_id=session_id) or []

        if not leads:
            continue

        req_update = leads_differences_exists(
            prev_leads=prev_leads,
            leads=leads
        )

        if req_update:
            try:
                await replyed.edit_reply_markup(
                    reply_markup=generate_leads_statuses_kb(leads=leads)
                )
            except Exception as e:
                print(e)

        if all_threads_ended(leads=leads):
            await asyncio.sleep(1)
            return await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"✅<b>Сессия #{session_id} завершена</b>"
            )

        if time.time() - START_POLLING > 60*60:
            await asyncio.sleep(1)
            return await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"❌Сессия #{session_id} завершена по 1 часовому "
                     "таймауту!"
            )

        prev_leads = leads

        await asyncio.sleep(1.1)


@router.message(PaymentCodeSettingForm.wait_payment_code)
@db_services_provider(provide_gologin=False)
async def set_payment_code(
        message: Message, state: FSMContext,
        leadsdb: LeadGenerationResultsService
):
    state_data = dict(await state.get_data())

    bot_reply_msg_id, session_id, lead_id = state_data.values()

    if bot_reply_msg_id:
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=bot_reply_msg_id
        )

    user_code, chat_id = message.text, message.chat.id

    await message.delete()

    if not user_code.isdigit() or len(user_code) != 4:
        bot_reply_msg_id = await message.bot.send_message(
            chat_id=chat_id,
            text="❌<b>Неверный формат!</b> Введите заново"
        )

        return await state.set_data(
            data=state_data | {"bot_message_id": bot_reply_msg_id}
        )

    await state.clear()

    leadsdb.change_status(
        status=LeadGenResultStatus.CODE_RECEIVED,
        session_id=session_id,
        lead_id=lead_id,
        sms_code=message.text
    )