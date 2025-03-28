from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.handlers.data import UseSupervisorData
from bot.keyboards.inline import get_session_presets_kb

router = Router(name=__name__)


@router.callback_query(UseSupervisorData.filter())
async def preset_supervisor(
        query: CallbackQuery,
        callback_data: UseSupervisorData,
        state: FSMContext,
):
    await query.answer("🔮🔮🔮")

    data = dict(await state.get_data())

    await state.set_data(
        data=data | dict(supervised=callback_data.use)
    )

    await query.message.edit_reply_markup(
        reply_markup=get_session_presets_kb(
            current_sms_service=data.get("sms-service"),
            is_supervised=callback_data.use
        )
    )
