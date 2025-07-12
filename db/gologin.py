import time
from traceback import print_tb

from .base import DefaultApikeyRedisRepository


class GologinApikeysRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "gologin:apikey"
    _APIKEY_COUNTER_KEY = "gologin:counter"
    _ANNIHILATION_TIMEOUT: int = 90

    _last_annihilation_time: float = 0
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GologinApikeysRepository, cls).__new__(cls)

        return cls._instance

    @property
    def exists(self):
        return bool(self.get_current())

    @property
    def _current_gologin_apikey_name(self):
        return self._APIKEY_KEY+str(self.get_count())

    def annihilate_current(self, _forced: bool = False):
        print("ANNIHILATE CURRENT GOLOGIN")

        if (not _forced) and (time.time() - self._last_annihilation_time) < self._ANNIHILATION_TIMEOUT:
            return

        self._conn.delete(self._current_gologin_apikey_name)

        self._decrease_count()

        if not _forced:
            self._last_annihilation_time = time.time()

    def get_current(self) -> str | None:
        print("GET CURRENT GOLOGIN")

        if not self.get_count():
            return None

        print(f"GET CURRENT GOLOGIN APIKEY [COUNTER: {self.get_count()}]")

        return self._conn.get(name=self._current_gologin_apikey_name).decode()

    def set(self, new_apikey: str):
        print("SET NEW GOLOGIN APIKEY")

        self._increase_count()

        self._conn.set(name=self._current_gologin_apikey_name, value=new_apikey)

        return new_apikey

    def get_count(self):
        try:
            print(f"_GET_COUNT SUCCESS {self._conn.get(self._APIKEY_COUNTER_KEY).decode()}")
            return int((self._conn.get(self._APIKEY_COUNTER_KEY)).decode())
        except:
            print("_GET_COUNT EXCEPT")
            self._conn.set(self._APIKEY_COUNTER_KEY, 0)
            return self.get_count()

    def _increase_count(self):
        print("INCREASE COUNT")

        self._conn.set(self._APIKEY_COUNTER_KEY, self.get_count()+1)

    def _decrease_count(self):
        print("DECREASE COUNT")

        if self.get_count() == 0:
            raise ValueError(f"{"=|"*30}\n\n\nGOLOGIN APIKEYS ENDED [ОБНОВИ АПИКЛЮЧИ ГОЛОГИНА]\n\n\n{"=|"*30}")

        print(self.get_count()-1, "RESULT COUNTER")

        self._conn.set(self._APIKEY_COUNTER_KEY, self.get_count()-1)
