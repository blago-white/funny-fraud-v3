from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.data import (LeadStatusCallbackData,
                               LeadCallbackAction,
                               LeadStatusReverseData,
                               ForceLeadNewSmsData,
                               RestartSessionData)
from db.transfer import LeadGenResult, LeadGenResultStatus


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
        LeadGenResultStatus.FAILED: LeadCallbackAction.VIEW_ERROR,
        LeadGenResultStatus.WAIT_CODE: LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.CODE_RECEIVED: LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.CODE_INVALID: LeadCallbackAction.ADD_PAYMENT_CODE,
        LeadGenResultStatus.RESEND_CODE: LeadCallbackAction.ADD_PAYMENT_CODE,
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
                 f"#{result.lead_id}",
            callback_data=LeadStatusCallbackData(
                session_id=result.session_id,
                lead_id=result.lead_id,
                action=action
            ).pack()
        ))

    kb.append(kb_line)

    kb.append([
        InlineKeyboardButton(
            text="🚫Завершить лид ⚠🔶🔷",
            callback_data=LeadStatusReverseData(
                session_id=leads[0].session_id
            ).pack()
        ),
        InlineKeyboardButton(
            text="🔷Прислать новый код",
            callback_data=ForceLeadNewSmsData(
                session_id=leads[0].session_id
            ).pack()
        ),
    ])

    kb.append([
        InlineKeyboardButton(
            text="♻Рестарт сессии",
            callback_data=RestartSessionData(
                session_id=leads[0].session_id
            ).pack(),
        ),
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=kb
    )
