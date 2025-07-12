from aiogram.filters.callback_data import CallbackData


class LeadCallbackAction:
    ADD_PAYMENT_CODE = "p"
    VIEW_ERROR = "e"


class LeadStatusCallbackData(CallbackData, prefix="lead"):
    session_id: int
    lead_id: int
    action: str = LeadCallbackAction.ADD_PAYMENT_CODE


class LeadStatusReverseData(CallbackData, prefix="reverse"):
    session_id: int


class ForceLeadNewSmsData(CallbackData, prefix="new_sms"):
    session_id: int


class RestartSessionData(CallbackData, prefix="restart"):
    session_id: int


class LeadPaidData(CallbackData, prefix="paid"):
    session_id: int


class SMSServiceSelectorData(CallbackData, prefix="sms-selector"):
    sms_service: str


class UseSupervisorData(CallbackData, prefix="supervised"):
    use: bool


class StopSupersessionData(CallbackData, prefix="supersession-stop"):
    pass


class StrictLeadsCountModeData(CallbackData, prefix="strict-count-leads"):
    use_strict: bool
