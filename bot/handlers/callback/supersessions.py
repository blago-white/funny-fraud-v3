from aiogram import Router

from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData, CallbackQuery

from bot.handlers.data import StopSupersessionData


router = Router(name=__name__)


@router.callback_query(StopSupersessionData.filter())
async def stop_super_session(
        query: CallbackQuery,
        callback_data: StopSupersessionData,
        state: FSMContext,
):
    await query.answer("🚫 Следующих сессий не будет!")

    await state.set_data(
        data=dict(await state.get_data()) | {"stop-supersession": True}
    )

    await query.message.edit_text(text=query.message.text)
