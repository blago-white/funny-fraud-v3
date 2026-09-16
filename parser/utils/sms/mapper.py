from .herosms import HeroSMSCodesService
from .smscodex import CodexSMSCodesService
from .smshub import SmsHubSMSService
from .elsms import ElSmsSMSCodesService
from .helpersms import HelperSMSService

from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository,
                    HeroSmsServiceApikeyRepository,
                    CodexSmsServiceApikeyRepository)


class SMSHUB:
    KEY = "H"
    NAME = "Sms-Hub"


class ELSMS:
    KEY = "E"
    NAME = "El-Sms"


class HELPERSMS:
    KEY = "S"
    NAME = "Helper-Sms"


class HEROSMS:
    KEY = "R"
    NAME = "Hero-SMS"


class CODEXSMS:
    KEY = "X"
    NAME = "Codex-Sms"


SMS_SERVICES_MAPPER = {
    SMSHUB.KEY: SmsHubSMSService,
    ELSMS.KEY: ElSmsSMSCodesService,
    HELPERSMS.KEY: HelperSMSService,
    HEROSMS.KEY: HeroSMSCodesService,
    CODEXSMS.KEY: CodexSMSCodesService,
}

SMS_DB_REPOSITORY_MAPPER = {
    ELSMS.KEY: ElSmsServiceApikeyRepository(),
    HELPERSMS.KEY: HelperSmsServiceApikeyRepository(),
    SMSHUB.KEY: SmsHubServiceApikeyRepository(),
    HEROSMS.KEY: HeroSmsServiceApikeyRepository(),
    CODEXSMS.KEY: CodexSmsServiceApikeyRepository()
}
