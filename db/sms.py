from .base import DefaultApikeyRedisRepository


class SmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:apikey"
