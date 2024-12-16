import random
import time
from abc import ABCMeta

import redis


class BaseRedisService(metaclass=ABCMeta):
    _conn: redis.Redis = redis.Redis.from_url("redis://localhost:6379/0")

    def __init__(self, conn: redis.Redis = None):
        self._conn = conn or self._conn


class DefaultApikeyRedisRepository(BaseRedisService, metaclass=ABCMeta):
    _conn: redis.Redis
    _APIKEY_KEY: str = None

    @property
    def exists(self):
        return bool(self.get_current())

    def get_current(self) -> str | None:
        return (self._conn.get(name=self._APIKEY_KEY) or b"").decode()

    def set(self, new_apikey: str):
        self._conn.set(name=self._APIKEY_KEY, value=new_apikey)

        return new_apikey


class DefaulConcurrentRepository(BaseRedisService):
    _locked: str = False

    def lock(self, session_id: int, lead_id: int = "x"):
        if self._locked and self._locked != f"{session_id}-{lead_id}":
            return False

        self._locked = f"{session_id}-{lead_id}"
        return True

    def unlock(self):
        self._locked = False

    def wait_for_lock(self, session_id: int, lead_id: int = "x"):
        c = 0

        while c < 1500:
            if self.lock(session_id, lead_id):
                return True

            time.sleep(.01)
            c += 1

    @classmethod
    def locked(
            cls, only_session_id: bool = False,
            only_one_thread: bool = False,
            session_id_position: int = 1,
            lead_id_position: int = 2,
            session_id_kwarg: str = "session_id",
            lead_id_kwarg: str = "lead_id"):
        def wrapper(func):
            def wrapped(*args, **kwargs):
                self: DefaulConcurrentRepository = args[0]

                if not issubclass(type(self), cls):
                    raise TypeError("Not correct decorator place")

                session_id = kwargs.get(
                    session_id_kwarg, args[session_id_position % len(args)]
                )

                if not only_session_id:
                    lead_id = kwargs.get(
                        lead_id_kwarg, args[lead_id_position % len(args)]
                    )
                else:
                    lead_id = None if not only_one_thread else (
                        random.randint(1000, 2000)
                    )

                self.wait_for_lock(session_id=session_id,
                                   lead_id=lead_id)

                result = func(*args, **kwargs)

                self.unlock()

                return result

            return wrapped

        return wrapper
