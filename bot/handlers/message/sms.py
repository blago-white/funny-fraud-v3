from aiogram import F
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.states.forms import SmsServiceApikeySettingForm
from db.sms import SmsServiceApikeyRepository

from ..common import db_services_provider


router = Router(name=__name__)


@router.message(F.text == "🔄Указать El-Sms Apikey")
async def make_reset_apikey(message: Message, state: FSMContext):
    await state.set_state(state=SmsServiceApikeySettingForm.wait_apikey)

    await message.bot.send_message(
        chat_id=message.chat.id,
        text="🔄Укажите новый apikey:\n"
             "<i>Если нажали по ошибке отправьте любой символ</i>",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(SmsServiceApikeySettingForm.wait_apikey)
@db_services_provider(provide_leads=False,
                      provide_gologin=False,
                      provide_sms=True)
async def set_apikey(message: Message, state: FSMContext,
                     smsdb: SmsServiceApikeyRepository):
    await state.clear()

    if not len(message.text) > 3:
        return await message.reply("✅Ввод отменен")

    smsdb.set(new_apikey=message.text.replace(" ", ""))

    await message.reply(
        text=f"✅Ключ сохранен:\n\n <code>{smsdb.get_current()}</code>"
    )
