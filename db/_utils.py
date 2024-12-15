from .transfer import LeadGenResultStatus, BLOCKING_STATUS_CODES


def code_is_blocking(status: LeadGenResultStatus) -> bool:
    return status in BLOCKING_STATUS_CODES
