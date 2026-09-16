from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.states.forms import SmsServiceApikeySettingForm
from parser.utils.sms.mapper import ELSMS, SMSHUB, HELPERSMS, \
    SMS_DB_REPOSITORY_MAPPER, HEROSMS, CODEXSMS
from ..common import db_services_provider

router = Router(name=__name__)


async def _process_change_sms_apikey(
        message: Message,
        state: FSMContext,
        sms_service_key: str):
    await state.set_state(state=SmsServiceApikeySettingForm.wait_apikey)
    await state.set_data(data={"sms-service": sms_service_key})

    await message.bot.send_message(
        chat_id=message.chat.id,
        text="🔄Укажите новый apikey:\n"
             "<i>Если нажали по ошибке отправьте любой символ</i>",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text == "☎ El-Sms Apikey")
async def make_reset_elsms_apikey(message: Message, state: FSMContext):
    await _process_change_sms_apikey(
        message=message,
        state=state,
        sms_service_key=ELSMS.KEY
    )


@router.message(F.text == "☎ Sms-Hub Apikey")
async def make_reset_smshub_apikey(message: Message, state: FSMContext):
    await _process_change_sms_apikey(
        message=message,
        state=state,
        sms_service_key=SMSHUB.KEY
    )


@router.message(F.text == "☎ Helper-Sms Apikey")
async def make_reset_smshub_apikey(message: Message, state: FSMContext):
    await _process_change_sms_apikey(
        message=message,
        state=state,
        sms_service_key=HELPERSMS.KEY
    )


@router.message(F.text == "☎ Hero-Sms Apikey")
async def make_reset_herosms_apikey(message: Message, state: FSMContext):
    await _process_change_sms_apikey(
        message=message,
        state=state,
        sms_service_key=HEROSMS.KEY
    )


@router.message(F.text == "☎ Codex-Sms Apikey")
async def make_reset_herosms_apikey(message: Message, state: FSMContext):
    await _process_change_sms_apikey(
        message=message,
        state=state,
        sms_service_key=CODEXSMS.KEY
    )


@router.message(SmsServiceApikeySettingForm.wait_apikey)
@db_services_provider(provide_leads=False,
                      provide_gologin=False)
async def set_apikey(message: Message, state: FSMContext):
    if not len(message.text) > 3:
        return await message.reply("✅Ввод отменен")

    apikey_repo = SMS_DB_REPOSITORY_MAPPER[
        (await state.get_data()).get("sms-service")
    ]

    apikey_repo.set(new_apikey=message.text.replace(" ", ""))

    await state.clear()

    await message.reply(
        text=f"✅Ключ сохранен:\n\n <code>{apikey_repo.get_current()}</code>"
    )
