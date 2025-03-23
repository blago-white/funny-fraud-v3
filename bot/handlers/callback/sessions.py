from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.filters.callback_data import CallbackData, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.handlers.data import (LeadStatusCallbackData,
                               LeadCallbackAction,
                               LeadStatusReverseData,
                               ForceLeadNewSmsData,
                               RestartSessionData,
                               LeadPaidData)
from db.leads import LeadGenerationResultsService
from bot.states.forms import PaymentCodeSettingForm
from ..common import db_services_provider

router = Router(name=__name__)


@router.callback_query(LeadStatusCallbackData.filter(
    F.action == LeadCallbackAction.ADD_PAYMENT_CODE
))
async def set_otp_code(
        query: CallbackQuery,
        callback_data: CallbackData,
        state: FSMContext):
    await state.set_state(state=PaymentCodeSettingForm.wait_payment_code)

    await query.answer(text="❇Отправьте код❇")


@router.callback_query(LeadStatusCallbackData.filter(
    F.action == LeadCallbackAction.VIEW_ERROR
))
@db_services_provider(provide_gologin=False)
async def view_lead_error(
        query: CallbackQuery, callback_data: CallbackData,
        leadsdb: LeadGenerationResultsService):
    await query.answer("ℹОжидайтеℹ")

    session_id, lead_id = callback_data.session_id, callback_data.lead_id

    lead = leadsdb.get(session_id=session_id, lead_id=lead_id)

    if not lead:
        await query.bot.send_message(
            chat_id=query.message.chat.id,
            text="❌ Запрашиваемый лид не существует"
        )

    await query.bot.send_message(
        chat_id=query.message.chat.id,
        text=f"❌ Ошибка лида SID:{session_id} LID:{lead_id}\n\n"
             f"{lead[0].error}"
    )


@router.callback_query(LeadStatusReverseData.filter(
    F.session_id != None
))
@db_services_provider(provide_gologin=False)
async def reverse_lead_status(
        query: CallbackQuery, callback_data: CallbackData,
        leadsdb: LeadGenerationResultsService):
    print("REVERSED")

    try:
        dropped = leadsdb.drop_waiting_lead(
            session_id=callback_data.session_id
        )
    except Exception as e:
        print(f"REVERSED ERROR {repr(e)} {e}")
        dropped = False

    if not dropped:
        await query.answer("⚠Не найдено лидов ожидающих кода⚠")
    else:
        await query.answer("✅Статус сброшен✅")


@router.callback_query(ForceLeadNewSmsData.filter(
    F.session_id != None
))
@db_services_provider(provide_gologin=False)
async def force_new_sms(
        query: CallbackQuery, callback_data: CallbackData,
        leadsdb: LeadGenerationResultsService):
    print("FORCES NEW SMS")

    try:
        dropped = leadsdb.force_new_sms(
            session_id=callback_data.session_id
        )
    except Exception as e:
        print(f"FORCED ERROR {repr(e)} {e}")
        dropped = False

    if not dropped:
        await query.answer("⚠Не найдено лидов ожидающих кода⚠")
    else:
        await query.answer("✅Смс запрошено, ожидайте✅")


@router.callback_query(RestartSessionData.filter(
    F.session_id != None
))
@db_services_provider(provide_gologin=False)
async def drop_session(
        query: CallbackQuery, callback_data: CallbackData,
        leadsdb: LeadGenerationResultsService):
    print("RESTART SESSION")

    try:
        dropped = leadsdb.drop_session(
            session_id=callback_data.session_id
        )
    except Exception as e:
        print(f"RESTART ERROR {repr(e)} {e}")
        dropped = False

    if not dropped:
        await query.answer("⚠Не удалось⚠")
    else:
        await query.answer("✅Сессия сброшена✅")


@router.callback_query(LeadPaidData.filter())
@db_services_provider(provide_gologin=False)
async def set_lead_paid(
        query: CallbackQuery,
        callback_data: LeadPaidData,
        leadsdb: LeadGenerationResultsService
):
    try:
        leadsdb.set_paid(session_id=callback_data.session_id)
    except:
        await query.answer("❌ Ошибка изменения статуса")
    else:
        await query.answer("✅ Готово")
