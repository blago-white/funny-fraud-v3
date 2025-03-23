from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.handlers.data import UseSupervisorData

router = Router(name=__name__)


@router.callback_query(UseSupervisorData.filter())
async def preset_supervisor(
    query: CallbackQuery,
    callback_data: UseSupervisorData,
    state: FSMContext,
):
    await query.answer("🔮🔮🔮")

    await state.set_data(
        data=dict(await state.get_data()) | dict(supervised=callback_data.use)
    )
