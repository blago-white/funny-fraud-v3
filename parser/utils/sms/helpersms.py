import random
import threading
import time

from helper20sms.helper20sms import Helper20SMS, BadApiKeyProvidedException

from db.sms import HelperSmsServiceApikeyRepository

from .exceptions import NumberGettingException
from .base import BaseSmsService


class HelperSMSService(BaseSmsService):
    _sms_service: Helper20SMS = None
    SMS_TIMEOUT = 60*3

    def __init__(self, apikey: str = None,
                 sms_service: Helper20SMS = None):
        super().__init__(
            apikey=apikey or HelperSmsServiceApikeyRepository().get_current()
        )

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
                service_id=19031,
                max_price=20
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
            print("EXCEPTION", e)
            raise NumberGettingException(e)

        print("CHECK", response)

        if response.get("status") is True:
            try:
                return response.get("data").get("codes")[-1]
            except IndexError:
                return None

        return NumberGettingException(response.get("detail"))

    def cancel(self, phone_id: int):
        print(f"START CANCELING PHONE {phone_id}")

        if not phone_id:
            return True

        threading.Thread(target=self._cancel, args=(
            phone_id,
            self._apikey
        )).start()

    def _cancel(self, phone_id: int,
                sms_apikey: str,
                _sms_service_class: Helper20SMS = Helper20SMS):
        time.sleep(2*60)

        sms_service = _sms_service_class(api_key=sms_apikey)

        print(f"CANCELING PHONE {phone_id}")

        for _ in range(6):
            print(f"CANCEL TRY #{_} {phone_id}")
            try:
                response = sms_service.set_order_status(
                    order_id=phone_id,
                    status="CANCEL"
                )
            except Exception as e:
                print(f"CANNOT CANCEL PHONE - {e}")
            else:
                if response.get("status") is True:
                    return
                else:
                    print(f"CANCELING ERROR - {response}")

            time.sleep(random.randint(10, 25))
