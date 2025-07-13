import asyncio
import time

from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.inline import generate_leads_statuses_kb, \
    get_session_presets_kb
from bot.keyboards.reply import APPROVE_KB
from bot.keyboards.reply import MAIN_MENU_KB
from bot.states.forms import SessionForm, PaymentCodeSettingForm
from db.gologin import GologinApikeysRepository
from db.leads import LeadGenerationResultsService
from db.proxy import ProxyRepository
from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository)
from db.statistics import LeadsGenerationStatisticsService
from db.transfer import LeadGenResultStatus
from parser.main import LeadsGenerator
from parser.sessions import LeadsGenerationSession
from parser.utils.sms.base import BaseSmsService
from quotas.main import QuotasManager
from supervisor.sessions import SessionSupervisor
from . import _labels as labels
from ._transfer import SessionStatusPullingCallStack
from ._utils import all_threads_ended, leads_differences_exists, \
    get_sms_service
from ..common import db_services_provider, leads_service_provider

router = Router(name=__name__)


@router.message(CommandStart())
@db_services_provider(provide_leads=False,
                      provide_elsms=True,
                      provide_smshub=True,
                      provide_proxy=True,
                      provide_helper=TypeError)
async def start(
        message: Message, state: FSMContext,
        gologindb: GologinApikeysRepository,
        elsmsdb: ElSmsServiceApikeyRepository,
        smshubdb: SmsHubServiceApikeyRepository,
        helperdb: HelperSmsServiceApikeyRepository,
        proxydb: ProxyRepository):
    await state.clear()

    apikeys = {
        "gologin": gologindb.get_current(),
        "elsms": elsmsdb.get_current(),
        "smshub": smshubdb.get_current(),
        "helpersms": helperdb.get_current(),
    }

    gologin_count_apikeys = gologindb.get_count()

    proxy_ok, _ = proxydb.can_use

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"🏠<b>Меню Парсера</b>\n"
             f"🤖<b>Gologin apikey: {"✅" if apikeys.get("gologin") else "📛"}"
             f"<code>{
             apikeys.get("gologin")[:6] + '...' + apikeys.get("gologin")[-3:]
             if apikeys.get("gologin")
             else ""
             } [кол-во: {gologin_count_apikeys}]</code></b>\n\n"
             f"☎ <b>Смс-Сервисы:</b>\n"
             f"— <b>El-Sms apikey: {"✅" if apikeys.get("elsms") else "📛"}"
             f"<code>{
             apikeys.get("elsms")[:6] + '...' + apikeys.get("elsms")[-3:]
             if apikeys.get("elsms")
             else ""
             }</code></b>\n"
             f"— <b>Sms-Hub apikey: {"✅" if apikeys.get("smshub") else "📛"}"
             f"<code>{
             apikeys.get("smshub")[:6] + '...' + apikeys.get("smshub")[-3:]
             if apikeys.get("smshub")
             else ""
             }</code></b>\n"
             f"— <b>Helper-Sms apikey: {"✅" if apikeys.get("helpersms") else "📛"}"
             f"<code>{
             apikeys.get("helpersms")[:6] + '...' + apikeys.get("helpersms")[-3:]
             if apikeys.get("helpersms")
             else ""
             }</code></b>\n\n"
             f"🔐<b>Proxy: {"✅" if proxy_ok else "📛"}</b>\n\n"
             f"<b>Статистика за сегодня: /stats</b>",
        reply_markup=MAIN_MENU_KB
    )


@router.message(F.text == "🔥Новый Сеанс")
@db_services_provider(provide_leads=False,
                      provide_elsms=True,
                      provide_smshub=True,
                      provide_helper=True,
                      provide_proxy=True)
async def new_session(
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
    ref_links = message.text.split("\n")

    for link in ref_links:
        if (not link.startswith("https://")) or (" " in link):
            await message.reply("Неверный формат\n\n<i>нужна ссылка</i>")
            return

    current_session_form = dict(await state.get_data())
    await state.set_data(data=current_session_form | {
        "ref_links": ref_links
    })

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

    await message.reply(text="✅ Отлично, форма заполнена!\n",
                        reply_markup=APPROVE_KB)

    await message.reply(
        text=f"| Кол-во запросов: "
             f"{current_session_form.get("count_requests")}\n"
             f"| Реф. ссылки: <code>"
             f"{', '.join(current_session_form.get("ref_links"))}"
             f"</code>\n",
        reply_markup=get_session_presets_kb(),
    )


@router.message(SessionForm.approve_session)
@db_services_provider(provide_gologin=False)
@leads_service_provider
async def approve_session(
        message: Message, state: FSMContext,
        leadsdb: LeadGenerationResultsService,
        parser_service_class: LeadsGenerator
):
    if message.text != "✅Начать сеанс":
        await message.reply("✅Отменен")
        await state.clear()
        return

    data = await state.get_data()

    session_form = LeadsGenerationSession(
        ref_links=data.get("ref_links"),
        card=data.get("payments_card"),
        count=data.get("count_requests"),
    )

    overrided_session_timeout = int(data.get("timeout", 60 * 60))

    sms_service: BaseSmsService = get_sms_service(
        state_data=(dict(await state.get_data()))
    )()

    try:
        sms_service_balance = sms_service.balance
    except:
        sms_service_balance = None

    await state.clear()
    await state.set_state(state=PaymentCodeSettingForm.wait_payment_code)

    sended = await message.bot.send_message(
        chat_id=message.chat.id,
        text="<b>Ожидайте...</b>",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.bot.delete_message(chat_id=message.chat.id,
                                     message_id=sended.message_id)

    is_supervised = data.get("supervised", False)
    supervisor_message_label = "🔮 Сессия под управлением ИИ" if is_supervised else ""

    replyed = await message.bot.send_message(
        chat_id=message.chat.id,
        text=labels.SESSION_INFO.format(
            0, 0, 0, "Скоро будет", "...", supervisor_message_label
        ),
    )

    parser_service = parser_service_class(sms_service=sms_service)

    session_id = parser_service.mass_generate(data=session_form)

    await state.set_data(data={"bot_message_id": 0,
                               "session_id": session_id})

    if is_supervised:
        SessionSupervisor(
            session_id=session_id,
            timeout=overrided_session_timeout
        ).supervise_session()

    call_stack = SessionStatusPullingCallStack(
        initiator_message=replyed,
        sms_service=sms_service,
        session_id=session_id,
        default_sms_service_balance=sms_service_balance,
        session_timeout=overrided_session_timeout,
        supervisor_label=supervisor_message_label
    )

    await _start_session_keyboard_pooling(
        call_stack=call_stack,
    )

    state_data = dict(await state.get_data())

    await state.clear()

    return state_data, call_stack


@router.message(PaymentCodeSettingForm.wait_payment_code)
@db_services_provider(provide_gologin=False)
async def set_payment_code(
        message: Message, state: FSMContext,
        leadsdb: LeadGenerationResultsService
):
    state_data = dict(await state.get_data())

    try:
        bot_reply_msg_id, session_id = state_data.values()
    except:
        return await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌<b>Невозможно отправить код :(</b>"
        )

    if bot_reply_msg_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=bot_reply_msg_id
            )

            state_data.update(bot_message_id=0)
        except:
            pass

    user_code, chat_id = message.text, message.chat.id

    await message.delete()

    if not user_code.isdigit() or len(user_code) != 4:
        bot_reply_msg_id = await message.bot.send_message(
            chat_id=chat_id,
            text="❌<b>Неверный формат!</b> Введите заново"
        )

        await state.set_state(state=PaymentCodeSettingForm.wait_payment_code)

        return await state.set_data(
            data=state_data | {"bot_message_id": bot_reply_msg_id}
        )

    await state.set_data(state_data)

    leadsdb.send_sms_code(session_id=session_id, sms_code=message.text)


@db_services_provider(provide_gologin=False)
async def _start_session_keyboard_pooling(
        leadsdb: LeadGenerationResultsService,
        call_stack: SessionStatusPullingCallStack,
):
    if not QuotasManager().validate_quota:
        return

    sms_stat_middleware = call_stack.stats_middleware

    session_id, sms_service, prev_leads, START_POLLING = (
        call_stack.session_id,
        call_stack.sms_service,
        list(),
        time.time()
    )

    sms_service_balance, current_stats, prev_balance = (
        None, sms_stat_middleware.all_stats, None
    )

    sms_stat_middleware.allow_phone_receiving()

    while True:
        print("KAYBOARD UPDATE ============================")

        if not QuotasManager().validate_quota:
            return

        try:
            if not (leads := (leadsdb.get(session_id=session_id) or [])):
                await asyncio.sleep(5)
                continue

            sms_service_balance = _get_sms_service_balance(
                sms_service=sms_service
            )

            if True:
                if type(sms_service_balance) is float:
                    sms_service_balance_delta = (
                            call_stack.default_sms_service_balance -
                            sms_service_balance
                    )

                    if sms_service_balance_delta > (len(leads) * 9 * 2):
                        sms_stat_middleware.freeze_phone_receiving()
                    else:
                        sms_stat_middleware.allow_phone_receiving()

                try:
                    new_stats = [
                        now - on_start for now, on_start in zip(
                            sms_stat_middleware.all_stats, current_stats
                        )
                    ]

                    balance_delta = (
                            sms_service_balance - call_stack.default_sms_service_balance
                    ) if (type(sms_service_balance) is float) else "..."

                    await call_stack.initiator_message.edit_text(
                        text=labels.SESSION_INFO.format(*(
                            new_stats + [
                                sms_service_balance, balance_delta
                            ] + [call_stack.supervisor_label]
                        )),
                        reply_markup=generate_leads_statuses_kb(leads=leads)
                    )
                except Exception as e:
                    print(f"SESSION KB ERROR: {e}")

            if all_threads_ended(leads=leads):
                await _process_session_finish(
                    session_id=session_id,
                    leads=leads,
                    sms_stat_middleware=sms_stat_middleware,
                    delta_balance=(
                        call_stack.default_sms_service_balance -
                        sms_service_balance
                    ) if call_stack.default_sms_service_balance else None
                )

                return await call_stack.initiator_message.bot.send_message(
                    chat_id=call_stack.initiator_message.chat.id,
                    text=f"✅<b>Сессия #{session_id} завершена</b>"
                )

            if time.time() - START_POLLING > call_stack.session_timeout:
                await _process_session_finish(
                    session_id=session_id,
                    leads=leads,
                    sms_stat_middleware=sms_stat_middleware,
                    delta_balance=(
                        call_stack.default_sms_service_balance -
                        sms_service_balance
                    ) if call_stack.default_sms_service_balance else None
                )

                return await call_stack.initiator_message.bot.send_message(
                    chat_id=call_stack.initiator_message.chat.id,
                    text=f"❌Сессия #{session_id} завершена по 1 часовому "
                         "таймауту!"
                )
        except Exception as e:
            raise e

        await asyncio.sleep(5)


async def _process_session_finish(
        session_id, leads,
        sms_stat_middleware,
        delta_balance: float):
    _commit_session_results(
        session_id=session_id,
        leads=leads,
        delta_balance=delta_balance
    )

    sms_stat_middleware.allow_phone_receiving()

    await asyncio.sleep(1)


def _commit_session_results(session_id: int,
                            delta_balance: float,
                            leads: list):
    results = {}

    for l in leads:
        if not results.get(l.ref_link):
            results.update({l.ref_link: 0})

        results[l.ref_link] += int(l.status == LeadGenResultStatus.SUCCESS)

    for link in results:
        LeadsGenerationStatisticsService().add_leads_count(
            session_id=session_id,
            link=link,
            count_leads=results[link]
        )

    if delta_balance:
        LeadsGenerationStatisticsService().add_sms_delta_balance(session_id=session_id, delta=delta_balance)


def _get_sms_service_balance(sms_service: BaseSmsService):
    try:
        return sms_service.balance
    except ValueError:
        return "<i>Ошибка получения данных</i>"
    except NotImplementedError:
        return "<i>С этим сервисом баланс пока получить нельзя</i>"
