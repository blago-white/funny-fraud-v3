from aiogram import Router
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_session_presets_kb
from bot.handlers.data import StopSupersessionData, StrictLeadsCountModeData

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


@router.callback_query(StrictLeadsCountModeData.filter())
async def strict_leads_count_mode(
    query: CallbackQuery,
    callback_data: StrictLeadsCountModeData,
    state: FSMContext,
):
    data = dict(await state.get_data())

    data |= {"use-strict": callback_data.use_strict}

    await state.set_data(data=data)

    await query.message.edit_reply_markup(
        reply_markup=get_session_presets_kb(
            current_sms_service=data.get("sms-service"),
            is_supervised=data.get("supervised"),
            strict_mode=callback_data.use_strict
        )
    )
