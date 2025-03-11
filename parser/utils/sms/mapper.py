from .smshub import SmsHubSMSService
from .elsms import ElSmsSMSCodesService
from .helpersms import HelperSMSService


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
