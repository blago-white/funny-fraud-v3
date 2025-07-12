from enum import Enum

from .base import DefaultApikeyRedisRepository
from .base import BaseRedisService


class LatestSmsTypes(Enum):
    CODE = "C"
    PAYMENT = "P"
    UNDEFINED = "U"


class ElSmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:el-sms-apikey"


class SmsHubServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:sms-hub-apikey"


class HelperSmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:helper-sms-apikey"


class LatestMobileSmsTextService(BaseRedisService):
    def get(self) -> tuple[LatestSmsTypes, str]:
        latest_sms_text = self._conn.get("sms:latest-sms")

        if latest_sms_text is None:
            self._conn.append("sms:latest-sms", "")
            latest_sms_text = ""

        type_ = (
            LatestSmsTypes.PAYMENT
            if latest_sms_text == LatestSmsTypes.PAYMENT
            else (
                LatestSmsTypes.CODE
                if len(latest_sms_text) == 4 else
                LatestSmsTypes.UNDEFINED
            )
        )

        return type_, latest_sms_text

    def add(self, text: str = LatestSmsTypes.PAYMENT):
        self._conn.set("sms:latest-sms", text)
