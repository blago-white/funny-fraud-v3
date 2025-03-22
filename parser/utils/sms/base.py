from abc import ABCMeta, abstractmethod


class BaseSmsService(metaclass=ABCMeta):
    _apikey: str = None
    SMS_TIMEOUT: int = 90

    def __init__(self, apikey: str = None):
        self._apikey = apikey

    @property
    def balance(self):
        raise NotImplemented("Balance method not implemented on this service!")

    @abstractmethod
    def get_number(self) -> tuple[str, str]:
        ...

    @abstractmethod
    def check_code(self, phone_id: int) -> str | None:
        ...

    @abstractmethod
    def cancel(self, phone_id: int):
        ...
