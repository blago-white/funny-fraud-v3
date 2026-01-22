from .herosms import HeroSMSCodesService
from .smshub import SmsHubSMSService
from .elsms import ElSmsSMSCodesService
from .helpersms import HelperSMSService

from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository,
                    HeroSmsServiceApikeyRepository)


class SMSHUB:
    KEY = "H"


class ELSMS:
    KEY = "E"


class HELPERSMS:
    KEY = "S"


class HEROSMS:
    KEY = "R"


SMS_SERVICES_MAPPER = {
    SMSHUB.KEY: SmsHubSMSService,
    ELSMS.KEY: ElSmsSMSCodesService,
    HELPERSMS.KEY: HelperSMSService,
    HEROSMS.KEY: HeroSMSCodesService
}

SMS_DB_REPOSITORY_MAPPER = {
    ELSMS.KEY: ElSmsServiceApikeyRepository(),
    HELPERSMS.KEY: HelperSmsServiceApikeyRepository(),
    SMSHUB.KEY: SmsHubServiceApikeyRepository(),
    HEROSMS.KEY: HeroSmsServiceApikeyRepository()
}
