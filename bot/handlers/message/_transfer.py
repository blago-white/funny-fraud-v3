from aiogram.types import Message
from dataclasses import dataclass

from parser.utils.sms.base import BaseSmsService


@dataclass
class SessionStatusPullingCallStack:
    session_id: int
    sms_service: BaseSmsService
    initiator_message: Message
    default_sms_service_balance: float = None
    session_timeout: int = 60*60
