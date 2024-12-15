from .base import DefaultApikeyRedisRepository


class GologinApikeysRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "gologin:apikey"
