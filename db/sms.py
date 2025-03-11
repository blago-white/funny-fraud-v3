from .base import DefaultApikeyRedisRepository

from parser.utils.sms.mapper import ELSMS, SMSHUB, HELPERSMS


class ElSmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:el-sms-apikey"


class SmsHubServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:sms-hub-apikey"


class HelperSmsServiceApikeyRepository(DefaultApikeyRedisRepository):
    _APIKEY_KEY = "sms:helper-sms-apikey"


SMS_DB_REPOSITORY_MAPPER = {
    ELSMS.KEY: ElSmsServiceApikeyRepository(),
    HELPERSMS.KEY: HelperSmsServiceApikeyRepository(),
    SMSHUB.KEY: SmsHubServiceApikeyRepository()
}
