from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers import data
from db.transfer import LeadGenResult, LeadGenResultStatus
from parser.utils.sms import mapper


def _get_lead_status(status: str):
    return {
        LeadGenResultStatus.PROGRESS: "⬆",
        LeadGenResultStatus.WAIT_CODE: "⚠",
        LeadGenResultStatus.CODE_RECEIVED: "☑",
        LeadGenResultStatus.FAILED: "🚫",
        LeadGenResultStatus.SUCCESS: "✅",
        LeadGenResultStatus.CODE_INVALID: "🔶",
        LeadGenResultStatus.RESEND_CODE: "🔷",
        LeadGenResultStatus.WAIT_CODE_FAIL: "🚫⚠",
    }[status]


def _get_button_action(status: LeadGenResultStatus):
    return {
        LeadGenResultStatus.FAILED: data.LeadCallbackAction.VIEW_ERROR,
        LeadGenResultStatus.WAIT_CODE: data.LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.CODE_RECEIVED: data.LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.CODE_INVALID: data.LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.RESEND_CODE: data.LeadCallbackAction.ADD_PAYMENT_CODE,
    }.get(status, "")


def generate_leads_statuses_kb(leads: list[LeadGenResult]):
    kb, kb_line = [], []

    for result_id, result in enumerate(leads):
        if result_id % 2 == 0:
            kb.append(kb_line)
            kb_line = []

        action = _get_button_action(status=result.status)

        kb_line.append(InlineKeyboardButton(
            text=f"{_get_lead_status(status=result.status)} "
                 f"#{result.lead_id} | "
                 f"{result.ref_link}",
            callback_data=data.LeadStatusCallbackData(
                session_id=result.session_id,
                lead_id=result.lead_id,
                action=action
            ).pack()
        ))

    kb.append(kb_line)

    kb.append([
        InlineKeyboardButton(
            text="🚫Завершить лид ⚠🔶🔷",
            callback_data=data.LeadStatusReverseData(
                session_id=leads[0].session_id
            ).pack()
        ),
        InlineKeyboardButton(
            text="🔷Прислать новый код",
            callback_data=data.ForceLeadNewSmsData(
                session_id=leads[0].session_id
            ).pack()
        ),
    ])

    kb.append([
        InlineKeyboardButton(
            text="❇Лид оплачен",
            callback_data=data.LeadPaidData(
                session_id=leads[0].session_id
            ).pack(),
        ),
    ])

    kb.append([
        InlineKeyboardButton(
            text="♻Рестарт сессии",
            callback_data=data.RestartSessionData(
                session_id=leads[0].session_id
            ).pack(),
        ),
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=kb
    )


def get_session_presets_kb(
        current_sms_service: str = mapper.HELPERSMS.KEY,
        is_supervised: bool = False,
        strict_mode: bool = False,
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{
                "🚩" if current_sms_service == mapper.SMSHUB.KEY else ""
                }☎ Sms-Hub",
                callback_data=data.SMSServiceSelectorData(
                    sms_service=mapper.SMSHUB.KEY
                ).pack()
            ), InlineKeyboardButton(
                text=f"{
                "🚩" if current_sms_service == mapper.ELSMS.KEY else ""
                }☎ Еl-Sms",
                callback_data=data.SMSServiceSelectorData(
                    sms_service=mapper.ELSMS.KEY
                ).pack()
            ), InlineKeyboardButton(
                text=f"{
                "🚩" if current_sms_service == mapper.HELPERSMS.KEY else ""
                }☎ Helper",
                callback_data=data.SMSServiceSelectorData(
                    sms_service=mapper.HELPERSMS.KEY
                ).pack()
            )],
            [InlineKeyboardButton(
                text=f"{"✅" if is_supervised else ""}🔮 Оптимизировать с ИИ",
                callback_data=data.UseSupervisorData(use=not is_supervised).pack()
            )],
            [InlineKeyboardButton(
                text=f"{"✅" if strict_mode else ""}⚠ Четкое соблюд. кол-в'а лидов [СС]",
                callback_data=data.StrictLeadsCountModeData(
                    use_strict=not strict_mode
                ).pack()
            )]
        ]
    )


def get_supersession_canceling_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🚫 Прервать суперсессию",
                callback_data=data.StopSupersessionData().pack()
            )
        ]]
    )
