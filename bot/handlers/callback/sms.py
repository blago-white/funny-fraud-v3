from aiogram.dispatcher.router import Router
from aiogram.filters.callback_data import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_session_presets_kb
from ..data import SMSServiceSelectorData

router = Router(name=__name__)


@router.callback_query(SMSServiceSelectorData.filter())
async def select_sms_service(
        query: CallbackQuery,
        callback_data: SMSServiceSelectorData,
        state: FSMContext
):
    data = dict(await state.get_data())

    await state.set_data(
        data=data | {"sms-service": callback_data.sms_service}
    )

    try:
        await query.message.edit_reply_markup(
            reply_markup=get_session_presets_kb(
                current_sms_service=callback_data.sms_service,
                is_supervised=data.get("supervised"),
                strict_mode=data.get("use-strict")
            )
        )
    except:
        pass
