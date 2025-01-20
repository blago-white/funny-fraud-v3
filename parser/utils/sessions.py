from typing import TYPE_CHECKING

from db.transfer import LeadGenResultStatus, LeadGenResult
from parser.sessions import LeadsGenerationSession
from parser.parser.exceptions import TraficBannedError, RegistrationSMSTimeoutError, BadPhoneError, InitializingError

if TYPE_CHECKING:
    from parser.main import LeadsGenerator
else:
    LeadsGenerator = object


def session_results_commiter(func):
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
                    error="",
                )
            )

        print(f"LEAD #{lead_id} STARTED")

        while True:
            proxy = self._proxy_service.next()

            try:
                initializer = self._initializer(
                    payments_card=session.card,
                    driver=self._drivers_service.get_desctop(
                        proxy=proxy,
                        worker_id=(session_id * lead_id) + 1
                    )
                )
                break
            except Exception as e:
                print(f"LEAD #{lead_id} FAILED - {e} {repr(e)}")

        print(f"LEAD #{lead_id} BROWSER INITED")

        kwargs |= {"lead_id": lead_id,
                   "initializer": initializer,
                   "session": LeadsGenerationSession(
                       ref_link=session.ref_link,
                       card=session.card,
                   )}

        try:
            func(*args, **kwargs)
        except SystemExit:
            print(f"LEAD #{lead_id} SYSTEM EXIT 0")

            return SystemExit(1)
        except (TraficBannedError, InitializingError) as e:
            print(f"{e} {repr(e)} LEAD #{lead_id} RETRY NO PHONE GENERATION")

            try:
                initializer.driver.close()
                print(f"LEAD #{lead_id} DRIVER STOPPED")
            except:
                print(f"LEAD #{lead_id} CANT STOP DRIVER")

            return wrapped(*args,
                           **kwargs | {
                               "use_phone": (
                                   e.used_phone_id, e.used_phone_number
                               ),
                               "lead_id": lead_id
                           })
        except (RegistrationSMSTimeoutError, BadPhoneError, Exception) as e:
            print(f"{e} {repr(e)} LEAD #{lead_id} RETRY WITH PHONE GENERATION")

            try:
                initializer.driver.close()
                print(f"LEAD #{lead_id} DRIVER STOPPED")
            except:
                print(f"LEAD #{lead_id} CANT STOP DRIVER")

            return wrapped(*args, **kwargs | {"lead_id": lead_id})
        # except Exception as e:
            # print(f"LEAD #{lead_id} FATAL ERROR - {e} | {repr(e)}")
            #
            # return self._db_service.change_status(
            #     session_id=session_id,
            #     lead_id=lead_id,
            #     status=LeadGenResultStatus.FAILED,
            #     error=f"{repr(e)}\n\n{e}"
            # )
        finally:
            try:
                initializer.driver.close()
            except:
                print(f"LEAD #{lead_id} CANT STOP DRIVER")

        self._db_service.change_status(
            status=LeadGenResultStatus.SUCCESS,
            session_id=session_id,
            lead_id=lead_id,
        )

    return wrapped
