from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from parser.utils.sms.mapper import ELSMS, SMSHUB, SMS_SERVICES_MAPPER
from parser.utils.sms.elsms import ElSmsSMSCodesService
from parser.utils.sms.smshub import SmsHubSMSService
from bot.states.forms import SmsServiceApikeySettingForm
from db.sms import SmsHubServiceApikeyRepository, ElSmsServiceApikeyRepository

from ._utils import get_sms_service
from ..common import db_services_provider


router = Router(name=__name__)

async def _process_change_sms_apikey(message: Message,
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
        sms_service_key=SMSHUB.KEY
    )


@router.message(SmsServiceApikeySettingForm.wait_apikey)
@db_services_provider(provide_leads=False,
                      provide_gologin=False,
                      provide_elsms=True,
                      provide_smshub=True)
async def set_apikey(message: Message, state: FSMContext,
                     elsmsdb: ElSmsServiceApikeyRepository,
                     smshubdb: SmsHubServiceApikeyRepository):
    if not len(message.text) > 3:
        return await message.reply("✅Ввод отменен")

    if (await state.get_data()).get("sms-service") == ELSMS.KEY:
        apikey_repo = elsmsdb
    else:
        apikey_repo = smshubdb

    apikey_repo.set(new_apikey=message.text.replace(" ", ""))

    await state.clear()

    await message.reply(
        text=f"✅Ключ сохранен:\n\n <code>{apikey_repo.get_current()}</code>"
    )
