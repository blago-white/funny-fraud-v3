from db.transfer import LeadGenResult, LeadGenResultStatus

from parser.utils.sms.mapper import SMS_SERVICES_MAPPER, ELSMS


def leads_differences_exists(
        prev_leads: list[LeadGenResult],
        leads: list[LeadGenResult]) -> bool:
    if (len(prev_leads) != len(leads)) and len(leads):
        return True

    try:
        for prev_lead, lead in zip(prev_leads, leads, strict=True):
            if prev_lead.status != lead.status:
                return True
    except Exception as e:
        return False

    return False


def all_threads_ended(leads: list[LeadGenResult]) -> bool:
    return all([i.status in (
        LeadGenResultStatus.SUCCESS, LeadGenResultStatus.FAILED
    ) for i in leads])


def get_sms_service(state_data: dict) -> object:
    return SMS_SERVICES_MAPPER[
        state_data.get("sms-service"),
        ELSMS.KEY
    ]
