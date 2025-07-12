from .smshub import SmsHubSMSService
from .elsms import ElSmsSMSCodesService
from .helpersms import HelperSMSService

from db.sms import (ElSmsServiceApikeyRepository,
                    SmsHubServiceApikeyRepository,
                    HelperSmsServiceApikeyRepository)


class SMSHUB:
    KEY = "H"


class ELSMS:
    KEY = "E"


class HELPERSMS:
    KEY = "S"


SMS_SERVICES_MAPPER = {
    SMSHUB.KEY: SmsHubSMSService,
    ELSMS.KEY: ElSmsSMSCodesService,
    HELPERSMS.KEY: HelperSMSService
}

SMS_DB_REPOSITORY_MAPPER = {
    ELSMS.KEY: ElSmsServiceApikeyRepository(),
    HELPERSMS.KEY: HelperSmsServiceApikeyRepository(),
    SMSHUB.KEY: SmsHubServiceApikeyRepository()
}
