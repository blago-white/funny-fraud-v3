import os

import requests

from db.sms import HeroSmsServiceApikeyRepository

from .base import BaseSmsService
from .exceptions import NumberGettingException
from .middleware import SmsRequestsStatMiddleware


class HeroSMSCodesService(BaseSmsService):
    def __init__(self, apikey: str = None):
        super().__init__(
            apikey=apikey or HeroSmsServiceApikeyRepository().get_current()
        )

    @SmsRequestsStatMiddleware.counter_receive_phone
    def get_number(self):
        print("HERO SMS GET NUMBER")

        result = requests.get(
            url="https://hero-sms.com/stubs/handler_api.php"
                f"?api_key={self._apikey}&action=getNumber"
                f"&service=atu&country={os.environ.get("SMS_COUNTRY")}&maxPrice=0.6"
        ).text

        print("HERO SMS", result)

        if not result.startswith("ACCESS_NUMBER"):
            raise NumberGettingException(result)

        return result.split(":")[1:]

    def check_code(self, phone_id: int):
        result = requests.get(
            url="https://hero-sms.com/stubs/handler_api.php"
                f"?api_key={self._apikey}&action=getStatus&id={phone_id}"
        ).text

        if result.startswith("STATUS_WAIT_RETRY") or result.startswith("STATUS_OK"):
            return result.split(":")[-1]

        return None

    @SmsRequestsStatMiddleware.counter_cancel_phone
    def cancel(self, phone_id: int) -> bool:
        requests.get(
            url="https://hero-sms.com/stubs/handler_api.php"
                f"?api_key={self._apikey}&action=setStatus&id={phone_id}&status=8"
        )

        return True
