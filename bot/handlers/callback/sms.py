from aiogram.dispatcher.router import Router
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import generate_sms_service_selection_kb
from ..data import SMSServiceSelectorData

router = Router(name=__name__)


@router.callback_query(SMSServiceSelectorData.filter())
async def select_sms_service(
    query: CallbackQuery,
    callback_data: SMSServiceSelectorData,
    state: FSMContext
):
    await state.set_data(
        data=dict(await state.get_data()) | {"sms-service": callback_data.sms_service}
    )

    try:
        await query.message.edit_reply_markup(
            reply_markup=generate_sms_service_selection_kb(current=callback_data.sms_service)
        )
    except:
        pass
