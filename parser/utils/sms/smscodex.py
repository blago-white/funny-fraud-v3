import os
import requests
from typing import Optional

from db.sms import CodexSmsServiceApikeyRepository

from .base import BaseSmsService
from .exceptions import NumberGettingException
from .middleware import SmsRequestsStatMiddleware


class CodexSMSCodesService(BaseSmsService):
    BASE_URL = "https://smscodex.com/api/v1"

    def __init__(self, apikey: str = None):
        super().__init__(
            apikey=apikey or CodexSmsServiceApikeyRepository().get_current()
        )

        self.api_key = apikey or CodexSmsServiceApikeyRepository().get_current()
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    @SmsRequestsStatMiddleware.counter_receive_phone
    def get_number(self, service: str = "sber-id", country: str = 0, price_limit: float = 0.4) -> tuple[str, str]:
        url = f"{self.BASE_URL}/marketplace/fast-purchase/api/"
        payload = {
            "service_code": service,
            "country": str(country),
            "price_limit": price_limit
        }

        try:
            response = self.session.post(url, json=payload)
        except Exception as e:
            print("EEE")
            raise e

        data = response.json()
        print(data)

        order_id = data.get("id") or data.get("order_id") or data.get("data", {}).get("id")
        phone_number = data.get("phone") or data.get("phone_number") or data.get("data", {}).get("phone")

        if not order_id or not phone_number:
            print(data)
            msg = data.get("detail") or data.get("message") or data.get("msg") or "Неизвестная ошибка"
            raise NumberGettingException(f"Ошибка API при получении номера: {msg}")

        return str(order_id), str(phone_number)

    def check_code(self, phone_id: int | str) -> Optional[str]:
        url = f"{self.BASE_URL}/marketplace/orders/{phone_id}"

        response = self.session.get(url)
        if response.status_code == 404:
            return None

        data = response.json()

        print(data)
        sms_code = data.get("last_code")
        print(sms_code)

        return str(sms_code) if sms_code else None

    @SmsRequestsStatMiddleware.counter_cancel_phone
    def cancel(self, phone_id: int | str) -> bool:
        # url = f"{self.BASE_URL}/marketplace/orders/{phone_id}/cancel"
        #
        # response = self.session.post(url)
        # response.raise_for_status()
        # data = response.json()
        #
        # if isinstance(data, dict) and data.get("status") is False:
        #     raise NumberGettingException(f"Ошибка API при отмене номера: {data.get('msg', 'Неизвестная ошибка')}")

        return True

#
# fetch("https://www.emailnator.com/api/message-list", {
#   "headers": {
#     "accept": "application/json",
#     "accept-language": "ru",
#     "content-type": "application/json",
#     "priority": "u=1, i",
#     "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"YaBrowser\";v=\"26.8\", \"Yowser\";v=\"2.5\"",
#     "sec-ch-ua-mobile": "?0",
#     "sec-ch-ua-platform": "\"Windows\"",
#     "sec-fetch-dest": "empty",
#     "sec-fetch-mode": "cors",
#     "sec-fetch-site": "same-origin"
#   },
#   "referrer": "https://www.emailnator.com/inbox",
#   "body": "{\"email\":\"combtmp+08fw9@gmail.com\",\"limit\":20}",
#   "method": "POST",
#   "mode": "cors",
#   "credentials": "include"
# });
#
# fetch("https://www.emailnator.com/api/message/gp1.uX1l11RCcvIwC_fNQlhTRoQ2MY3prJ9vtAzYNpkscyjmcWIJm5bN6DaNdNcMzmZHE3sKkUzT1SkpXKgF8njZ83FBw-BzaJ6gOFk-2iIJcQ", {
#   "headers": {
#     "accept": "application/json",
#     "accept-language": "ru",
#     "content-type": "application/json",
#     "priority": "u=1, i",
#     "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"YaBrowser\";v=\"26.8\", \"Yowser\";v=\"2.5\"",
#     "sec-ch-ua-mobile": "?0",
#     "sec-ch-ua-platform": "\"Windows\"",
#     "sec-fetch-dest": "empty",
#     "sec-fetch-mode": "cors",
#     "sec-fetch-site": "same-origin"
#   },
#   "referrer": "https://www.emailnator.com/inbox/combtmp%2B08fw9%40gmail.com/gp1.uX1l11RCcvIwC_fNQlhTRoQ2MY3prJ9vtAzYNpkscyjmcWIJm5bN6DaNdNcMzmZHE3sKkUzT1SkpXKgF8njZ83FBw-BzaJ6gOFk-2iIJcQ",
#   "body": null,
#   "method": "GET",
#   "mode": "cors",
#   "credentials": "include"
# });
