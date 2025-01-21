import random
import time
from typing import TYPE_CHECKING
from requests.exceptions import JSONDecodeError

from db.transfer import LeadGenResultStatus, LeadGenResult
from parser.sessions import LeadsGenerationSession
from parser.parser.exceptions import TraficBannedError, RegistrationSMSTimeoutError, BadPhoneError, InitializingError, BadSMSService

if TYPE_CHECKING:
    from parser.main import LeadsGenerator
else:
    LeadsGenerator = object


def session_results_commiter(func):
    def _close_driver(drivers_service, pid, initializer):
        try:
            drivers_service.gologin_manager.delete_profile(pid=pid)
            initializer.driver.close()
            return True
        except:
            return False

    def wrapped(*args,
                _used_phone: str = None,
                _used_phone_id: int = None,
                lead_id: int = None,
                **kwargs):
        if len(args) > 1:
            raise ValueError("Only kwargs")

        self: LeadsGenerator = args[0]

        session_id, session = (
            kwargs.get("session_id"), kwargs.get("session")
        )

        session: LeadsGenerationSession

        if lead_id is None:
            _, lead_id = self._db_service.add(
                session_id=session_id,
                result=LeadGenResult(
                    session_id=session_id,
                    status=LeadGenResultStatus.PROGRESS,
                    ref_link=session.ref_link.split('?aff_id=')[-1].split("&")[0],
                    error="",
                )
            )

        print(f"LEAD #{lead_id} STARTED")

        for _ in range(10):
            time.sleep(lead_id*0.25)

            proxy = self._proxy_service.next()

            try:
                pid, driver = self._drivers_service.get_desctop(
                    proxy=proxy,
                    worker_id=(session_id * lead_id) + 1
                )
                break
            except JSONDecodeError as e:
                print(f"LEAD #{lead_id} GOLOGIN RESPONSE FAILED - {e} | {repr(e)}")

                return self._db_service.change_status(
                    session_id=session_id,
                    lead_id=lead_id,
                    status=LeadGenResultStatus.FAILED,
                    error=f"GOLOGIN RESPONSE FAILED: \n\n{repr(e)}\n\n{e}"
                )
            except Exception as e:
                print(f"LEAD #{lead_id} FAILED - {e} {repr(e)}")
        else:
            print(f"LEAD #{lead_id} CANT RUN GOLOGIN")
            return self._db_service.change_status(
                session_id=session_id,
                lead_id=lead_id,
                status=LeadGenResultStatus.FAILED,
                error=f"CANT RUN GOLOGIN AFTER 15 RETRY"
            )

        initializer = self._initializer(
            payments_card=session.card,
            driver=driver
        )

        print(f"LEAD #{lead_id} BROWSER INITED")

        kwargs |= {"lead_id": lead_id,
                   "initializer": initializer,
                   "session": LeadsGenerationSession(
                       ref_link=session.ref_link,
                       card=session.card,
                   )}

        try:
            func(*args, **kwargs)
        except (SystemExit, BadSMSService) as fatal_error:
            print(f"LEAD #{lead_id} FATAL ERROR {fatal_error} - {repr(fatal_error)}")

            if not (self._db_service.get(
                    session_id=session_id, lead_id=lead_id
            )[0].status == LeadGenResultStatus.FAILED):
                self._db_service.change_status(
                    session_id=session_id,
                    lead_id=lead_id,
                    status=LeadGenResultStatus.FAILED,
                    error=f"{repr(fatal_error)}\n\n{fatal_error}"
                )

            raise fatal_error
        except (TraficBannedError, InitializingError) as init_error:
            print(f"{init_error} {repr(init_error)} LEAD #{lead_id} RETRY NO PHONE GENERATION")

            _close_driver(initializer=initializer,
                          drivers_service=self._drivers_service,
                          pid=pid)

            return wrapped(
                *args,
                **kwargs | {
                    "use_phone": (
                        init_error.used_phone_id, init_error.used_phone_number
                    ),
                    "lead_id": lead_id
                }
            )
        except (RegistrationSMSTimeoutError, BadPhoneError, Exception) as e:
            print(f"{e} {repr(e)} LEAD #{lead_id} RETRY WITH PHONE GENERATION")

            _close_driver(initializer=initializer,
                          drivers_service=self._drivers_service,
                          pid=pid)

            return wrapped(*args, **kwargs | {"lead_id": lead_id})
        finally:
            _close_driver(initializer=initializer,
                          drivers_service=self._drivers_service,
                          pid=pid)

        self._db_service.change_status(
            status=LeadGenResultStatus.SUCCESS,
            session_id=session_id,
            lead_id=lead_id,
        )

    return wrapped
