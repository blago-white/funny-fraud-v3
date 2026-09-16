from dataclasses import dataclass, field
from enum import Enum

from parser.utils.mail.base import BaseEmailVerificationService
from parser.utils.mail.gmail import GmailVerificationService


class SessionStrategy(Enum):
    DEFAULT = "D"
    SBER_ID = "S"


@dataclass
class LeadsGenerationSession:
    card: str
    count: int = 1
    ref_links: list[str] = None
    ref_link: str = None
    mail_verification_service: BaseEmailVerificationService = GmailVerificationService
    strategy: SessionStrategy = SessionStrategy.DEFAULT
