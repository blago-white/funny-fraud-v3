import os
import requests
from typing import Optional

from db.sms import CodexSmsServiceApikeyRepository

from .base import BaseSmsService
from .exceptions import NumberGettingException
from .middleware import SmsRequestsStatMiddleware


class CodexSMSCodesService(BaseSmsService):
    BASE_URL = "https://smscodex.com/api/v1"
    _provider: str

    def __init__(self, apikey: str = None, sms_provider_id: str = None):
        super().__init__(
            apikey=apikey or CodexSmsServiceApikeyRepository().get_current()
        )

        self._provider = sms_provider_id or os.environ.get("DEFAULT_CODEXSMS_PROVIDER")

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
            "price_limit": price_limit,
            "provider_id": self._provider,
        }

        try:
            response = self.session.post(url, json=payload)
        except Exception as e:
            raise e

        data = response.json()

        order_id = data.get("id") or data.get("order_id") or data.get("data", {}).get("id")
        phone_number = data.get("phone") or data.get("phone_number") or data.get("data", {}).get("phone")

        if not order_id or not phone_number:
            msg = data.get("detail") or data.get("message") or data.get("msg") or "Неизвестная ошибка"
            raise NumberGettingException(f"Ошибка API при получении номера: {msg}")

        return str(order_id), str(phone_number.replace("+", ""))

    def check_code(self, phone_id: int | str) -> Optional[str]:
        url = f"{self.BASE_URL}/marketplace/orders/{phone_id}"

        response = self.session.get(url)
        if response.status_code == 404:
            return None

        data = response.json()

        sms_code = data.get("last_code")

        return str(sms_code) if sms_code else None

    @SmsRequestsStatMiddleware.counter_cancel_phone
    def cancel(self, phone_id: int | str) -> bool:
        url = f"{self.BASE_URL}/marketplace/orders/{phone_id}/cancel"

        response = self.session.post(url)
        try:
            data = response.json()

            if isinstance(data, dict) and data.get("status") is False:
                raise NumberGettingException(f"Ошибка API при отмене номера: {data.get('msg', 'Неизвестная ошибка')}")
        except Exception as e:
            print("NUMBER CANCELING ERROR", type(e), e)
            return
