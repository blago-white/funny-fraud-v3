from typing import TYPE_CHECKING

from db.transfer import LeadGenResultStatus, LeadGenResult
from parser.sessions import LeadsGenerationSession
from parser.parser.exceptions import TraficBannedError

if TYPE_CHECKING:
    from parser.main import LeadsGenerator
else:
    LeadsGenerator = object


def session_results_commiter(func):
    def wrapped(*args, **kwargs):
        if len(args) > 1:
            raise ValueError("Only kwargs")

        self: LeadsGenerator = args[0]

        session_id, session = (
            kwargs.get("session_id"), kwargs.get("session")
        )

        session: LeadsGenerationSession

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
                print(f"LEAD #{lead_id} FAILED ")

        print(f"LEAD #{lead_id} BROWSER INITED")

        kwargs |= {"lead_id": lead_id,
                   "initializer": initializer,
                   "session": LeadsGenerationSession(
                       ref_link=session.ref_link,
                       card=session.card,
                   )}

        try:
            func(*args, **kwargs)
        except TraficBannedError as e:
            return wrapped(*args, **kwargs)
        except Exception as e:
            return self._db_service.change_status(
                session_id=session_id,
                lead_id=lead_id,
                status=LeadGenResultStatus.FAILED,
                error=f"{repr(e)}\n\n{e}"
            )
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
