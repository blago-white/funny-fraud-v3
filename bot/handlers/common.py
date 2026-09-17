from functools import wraps
from typing import Type

from db.gologin import GologinApikeysRepository
from db.leads import LeadGenerationResultsService
from db.proxy import ProxyRepository
from db.sms import (
    ElSmsServiceApikeyRepository,
    SmsHubServiceApikeyRepository,
    HelperSmsServiceApikeyRepository,
    HeroSmsServiceApikeyRepository,
    CodexSmsServiceApikeyRepository
)
from db.statistics import LeadsGenerationStatisticsService
from parser.main import LeadsGenerator


SERVICES_REGISTRY: dict[str, tuple[str, Type]] = {
    "provide_leads": ("leadsdb", LeadGenerationResultsService),
    "provide_gologin": ("gologindb", GologinApikeysRepository),
    "provide_elsms": ("elsmsdb", ElSmsServiceApikeyRepository),
    "provide_smshub": ("smshubdb", SmsHubServiceApikeyRepository),
    "provide_helper": ("helperdb", HelperSmsServiceApikeyRepository),
    "provide_herosms": ("herosmsdb", HeroSmsServiceApikeyRepository),
    "provide_codexsms": ("codexsmsdb", CodexSmsServiceApikeyRepository),
    "provide_proxy": ("proxydb", ProxyRepository),
    "provide_stats": ("statsdb", LeadsGenerationStatisticsService),
}

DEFAULT_FLAGS = {
    "provide_leads": True,
    "provide_gologin": True,
}


def db_services_provider(**flags):
    enabled_flags = {**DEFAULT_FLAGS, **flags}

    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            db_services = {}

            for flag, enabled in enabled_flags.items():
                if enabled and flag in SERVICES_REGISTRY:
                    kw_name, factory = SERVICES_REGISTRY[flag]
                    db_services[kw_name] = factory()

            return await func(*args, **kwargs, **db_services)

        return wrapped

    return wrapper


def leads_service_provider(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        return await func(*args, **kwargs, parser_service_class=LeadsGenerator)

    return wrapped
