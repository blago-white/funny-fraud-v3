import requests

from db.sms import SmsHubServiceApikeyRepository

from .exceptions import NumberGettingException
from .base import BaseSmsService
from .middleware import SmsRequestsStatMiddleware


class SmsHubSMSService(BaseSmsService):
    def __init__(self, apikey: str = None):
        super().__init__(
            apikey=apikey or SmsHubServiceApikeyRepository().get_current()
        )

    @SmsRequestsStatMiddleware.counter_receive_phone
    def get_number(self):
        print("SMSHUB GET NUMBER")

        result = requests.get(
            url="https://smshub.org/stubs/handler_api.php"
                f"?api_key={self._apikey}&action=getNumber"
                "&service=atu&country=russia&maxPrice=0.12"
        ).text

        print("SMSHUB", result)

        if not result.startswith("ACCESS_NUMBER"):
            raise NumberGettingException(result)

        return result.split(":")[1:]

    def check_code(self, phone_id: int):
        result = requests.get(
            url="https://smshub.org/stubs/handler_api.php"
                f"?api_key={self._apikey}&action=getStatus&id={phone_id}"
        ).text

        if result.startswith("STATUS_WAIT_RETRY") or result.startswith("STATUS_OK"):
            return result.split(":")[-1]

        return None

    @SmsRequestsStatMiddleware.counter_cancel_phone
    def cancel(self, phone_id: int):
        pass
