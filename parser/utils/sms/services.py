import os

import requests

from db.sms import SmsServiceApikeyRepository

from .exceptions import NumberGettingException


class SmsCodesService:
    _id: str
    _apikey: str = None

    def __init__(self, apikey: str = None):
        self._apikey = apikey or SmsServiceApikeyRepository().get_current()

    def get_number(self, retries: int = 3) -> str:
        print("SMS_APIKEY", self._apikey)

        response = requests.get(
            url=f"https://el-sms.com/api/orderPhone/"
                f"?api_key={self._apikey}&v=1.4&country=ru&service=2908"
        )

        if response.status_code == 202 and not retries:
            raise NumberGettingException(response.text)
        elif response.status_code == 202 and retries:
            return self.get_number(retries=retries-1)

        result = response.json()

        return result["message"]["id"], str(result["message"]["phone"])

    def check_code(self, phone_id: int):
        response = requests.get(
            url=f"https://el-sms.com/api/getPhoneInfo/"
                f"?api_key={self._apikey}&v=1.4"
                f"&id={phone_id}"
        )

        if response.status_code == 202:
            raise NumberGettingException(response.text)

        result = response.json()

        try:
            return result["message"]["codes"][-1]
        except:
            return None
