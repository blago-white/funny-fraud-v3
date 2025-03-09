from .smshub import SmsHubSMSService
from .elsms import ElSmsSMSCodesService


class SMSHUB:
    KEY = "H"


class ELSMS:
    KEY = "E"


SMS_SERVICES_MAPPER = {
    SMSHUB.KEY: SmsHubSMSService,
    ELSMS.KEY: ElSmsSMSCodesService,
}
