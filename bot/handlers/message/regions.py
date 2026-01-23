import dotenv
from aiogram.dispatcher.router import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("kz"))
async def set_kz_region(message: Message, state: FSMContext):
    dotenv.set_key(dotenv_path=".env", key_to_set="SMS_COUNTRY", value_to_set="2")

    await message.reply("Регион изменен на Казахстан 🇰🇿\n\n"
                        "<b>Не забудь изменить прокси на прокси нужного региона!</b>")


@router.message(Command("ru"))
async def set_ru_region(message: Message, state: FSMContext):
    dotenv.set_key(dotenv_path=".env", key_to_set="SMS_COUNTRY", value_to_set="0")

    await message.reply("Регион изменен на Россию 🇷🇺\n\n"
                        "<b>Не забудь изменить прокси на прокси нужного региона!</b>")
