from db.transfer import LeadGenResult, LeadGenResultStatus


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
