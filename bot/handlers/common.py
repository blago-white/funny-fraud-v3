from functools import wraps

from parser.main import LeadsGenerator
from db.leads import LeadGenerationResultsService
from db.gologin import GologinApikeysRepository
from db.sms import SmsServiceApikeyRepository
from parser.utils.sms.services import SmsCodesService


def db_services_provider(provide_leads: bool = True,
                         provide_gologin: bool = True,
                         provide_sms: bool = False):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            db_services = {}

            if provide_leads:
                db_services.update(leadsdb=LeadGenerationResultsService())

            if provide_gologin:
                db_services.update(gologindb=GologinApikeysRepository())

            if provide_sms:
                db_services.update(smsdb=SmsServiceApikeyRepository())

            return await func(*args, **kwargs, **db_services)

        return wrapped
    return wrapper


def leads_service_provider(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        return await func(*args, **kwargs, parser_service=LeadsGenerator())

    return wrapped
