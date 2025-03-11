from functools import wraps

from parser.main import LeadsGenerator
from db.leads import LeadGenerationResultsService
from db.gologin import GologinApikeysRepository
from db.sms import ElSmsServiceApikeyRepository, SmsHubServiceApikeyRepository, HelperSmsServiceApikeyRepository
from db.proxy import ProxyRepository
from parser.utils.sms.elsms import ElSmsSMSCodesService


def db_services_provider(provide_leads: bool = True,
                         provide_gologin: bool = True,
                         provide_elsms: bool = False,
                         provide_smshub: bool = False,
                         provide_helper: bool = False,
                         provide_proxy: bool = False):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            db_services = {}

            if provide_leads:
                db_services.update(leadsdb=LeadGenerationResultsService())

            if provide_gologin:
                db_services.update(gologindb=GologinApikeysRepository())

            if provide_elsms:
                db_services.update(elsmsdb=ElSmsServiceApikeyRepository())

            if provide_smshub:
                db_services.update(smshubdb=SmsHubServiceApikeyRepository())

            if provide_helper:
                db_services.update(helperdb=HelperSmsServiceApikeyRepository())

            if provide_proxy:
                db_services.update(proxydb=ProxyRepository())

            return await func(*args, **kwargs, **db_services)

        return wrapped
    return wrapper


def leads_service_provider(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        return await func(*args, **kwargs, parser_service_class=LeadsGenerator)

    return wrapped
