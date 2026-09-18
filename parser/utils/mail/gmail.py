import json

import requests
from typing import Callable

from .exceptions import CannotReceiveMailAddrError
from parser.utils.mail.base import BaseEmailVerificationService

from ._otp_extractor import extract_otp_from_mail


class GmailVerificationService(BaseEmailVerificationService):
    _BASE_URL = "https://www.emailnator.com/api/"

    def __init__(self, extract_otp_code_function: Callable = extract_otp_from_mail):
        self._extract_otp = extract_otp_code_function

    def get_mail(self, _r = 3):
        if _r == 0:
            raise CannotReceiveMailAddrError(
                "Cannot receive gmail addres for verification trought API! "
                "[3 retry failed]"
            )

        if self._email:
            return self._email

        response = requests.post(
            self._BASE_URL + "/generate-email",
            data=json.dumps({"ids": [3]})
        ).json()

        if response["status"] == "success":
            if "+" in response["email"]:
                return self.get_mail(_r=_r-1)

            self._email = response["email"]

            return self._email

        return self.get_mail(_r=_r-1)

    def get_code(self) -> str:
        if not self._email:
            raise ValueError("Email addr not received before!")

        msg_id = self._get_otp_message_id()

        if not msg_id:
            return None

        return self._get_otp_code_from_message(msg_id=msg_id)

    def _get_otp_code_from_message(self, msg_id: str) -> str:
        msg = requests.get(
            self._BASE_URL + "message/" + msg_id,
        ).json()

        return self._extract_otp(msg["content"])

    def _get_otp_message_id(self) -> str:
        msg_list = requests.post(
            self._BASE_URL + "message-list/",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"email": self._email, "limit": 20})
        ).json()

        print(*msg_list, sep="\n")

        if msg_list["status"] != "success":
            raise ValueError("Gmail API Error")

        try:
            return [msg["id"] for msg in msg_list["messages"] if msg["subject"] == "Код для входа в Сайт СберБанка"][0]
        except IndexError:
            return None
