from dataclasses import dataclass


@dataclass
class LeadGenResultStatus:
    WAIT_CODE = "w"
    WAIT_CODE_FAIL = "l"
    CODE_RECEIVED = "c"
    CODE_INVALID = "i"
    RESEND_CODE = "e"
    FAILED = "f"
    SUCCESS = "s"
    PROGRESS = "r"


STATUS_MAPPING = {
    "r": LeadGenResultStatus.PROGRESS,
    "w": LeadGenResultStatus.WAIT_CODE,
    "c": LeadGenResultStatus.CODE_RECEIVED,
    "f": LeadGenResultStatus.FAILED,
    "s": LeadGenResultStatus.SUCCESS,
    "i": LeadGenResultStatus.CODE_INVALID,
    "e": LeadGenResultStatus.RESEND_CODE,
    "l": LeadGenResultStatus.WAIT_CODE_FAIL
}

BLOCKING_STATUS_CODES = [
    LeadGenResultStatus.WAIT_CODE,
    LeadGenResultStatus.CODE_RECEIVED,
    LeadGenResultStatus.CODE_INVALID,
    LeadGenResultStatus.RESEND_CODE,
    LeadGenResultStatus.WAIT_CODE_FAIL
]


@dataclass
class LeadGenResult:
    session_id: int
    status: str = None
    error: str | None = None
    proxy: str | None = None
    sms_code: str | None = None

    lead_id: int | None = None

    def __post_init__(self):
        self.status = STATUS_MAPPING.get(self.status, "f")
