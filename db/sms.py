from .base import DefaultApikeyRedisRepository


class ElSmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:el-sms-apikey"


class SmsHubServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:sms-hub-apikey"
