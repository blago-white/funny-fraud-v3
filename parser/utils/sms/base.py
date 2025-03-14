from abc import ABCMeta, abstractmethod


class BaseSmsService(metaclass=ABCMeta):
    _apikey: str = None

    def __init__(self, apikey: str = None):
        self._apikey = apikey

    @abstractmethod
    def get_number(self) -> tuple[str, str]:
        ...

    @abstractmethod
    def check_code(self, phone_id: int) -> str | None:
        ...

    @abstractmethod
    def cancel(self, phone_id: int):
        ...
