from helper20sms.helper20sms import Helper20SMS, BadApiKeyProvidedException

from .exceptions import NumberGettingException
from .base import BaseSmsService


class HelperSMSService(BaseSmsService):
    _sms_service: Helper20SMS = None

    def __init__(self, *args,
                 sms_service: Helper20SMS = None,
                 **kwargs):
        super().__init__(*args, **kwargs)

        self._sms_service = sms_service or Helper20SMS(
            api_key=self._apikey
        )

        try:
            print(f"HELPER SMS BALANCE: {self._sms_service.get_balance()}")
        except BadApiKeyProvidedException:
            raise PermissionError("Bad SMS HELPER apikey!")

    def get_number(self) -> tuple[str, str]:
        print("HELPER SMS GET NUMBER")

        try:
            response = self._sms_service.get_number(
                service_id=19031, in_bot_notifications=True
            )
        except Exception as e:
            raise NumberGettingException(e)

        if response.get("status") is True:
            return response.get("data").get("order_id"), response.get("data").get("number")

        raise NumberGettingException(response.get("detail"))

    def check_code(self, phone_id: int) -> str | None:
        try:
            response = self._sms_service.get_codes(order_id=phone_id)
        except Exception as e:
            raise NumberGettingException(e)

        if response.get("status") is True:
            return response.get("data").get("codes")[-1]

        return NumberGettingException(response.get("detail"))
