import random
import time

from .base import DefaulConcurrentRepository
from .transfer import LeadGenResult, LeadGenResultStatus, STATUS_MAPPING
from ._utils import code_is_blocking


class LeadGenerationResultsService(DefaulConcurrentRepository):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(LeadGenerationResultsService, cls).__new__(
                cls
            )
        return cls.instance

    def get_count(self) -> int:
        try:
            return int(self._conn.get("sessions:count"))
        except:
            self._init_sessions_counter()
            return self.get_count()

    def increase_count(self):
        pipe = self._conn.pipeline()

        current = self.get_count()
        current += 1

        pipe.set(name="sessions:count", value=current)
        pipe.execute()

    @DefaulConcurrentRepository.locked(only_session_id=True)
    def init(self, session_id: int):
        if self._conn.get(f"sessions:session#{session_id}"):
            return

        self._conn.append(f"sessions:session#{session_id}",
                          "")

        self.increase_count()

        return True

    def get(self, session_id: int, lead_id: int = None) -> list[LeadGenResult]:
        try:
            leads = self._conn.get(f"sessions:session#{session_id}").decode(
                "utf-8"
            )

            assert bool(leads) is True, ValueError
        except:
            return []

        leads = [i for i in leads.split("&") if i]

        session_leads = [LeadGenResult(
            session_id=session_id,
            lead_id=int(l.split("@")[0]),
            status=STATUS_MAPPING.get(l.split("@")[1],
                                      LeadGenResultStatus.FAILED),
            sms_code=l.split("@")[2],
            error=l.split("@")[3],
            proxy=l.split("@")[4]
        ) for l in leads]

        return [l for l in session_leads
                if not lead_id or l.lead_id == lead_id]

    @DefaulConcurrentRepository.locked(only_session_id=True,
                                       only_one_thread=True)
    def add(self, session_id: int, result: LeadGenResult):
        id_ = f"sessions:session#{session_id}"

        try:
            exists = self._conn.get(id_).decode("utf-8")
        except:
            self.init(session_id=session_id)
            exists = self._conn.get(id_).decode("utf-8")

        if not exists:
            self._conn.set(name=id_,
                           value=f"0@"
                                 f"{result.status}@"
                                 f"{result.sms_code}@"
                                 f"{result.error}@"
                                 f"{result.proxy}&"
                           )

            return id_, 0

        exists = [i for i in exists.split("&") if len(i) > 2]

        self._conn.set(name=id_,
                       value="&".join(exists + [
                           f"{len(exists)}@"
                           f"{result.status}@"
                           f"{result.sms_code}@"
                           f"{result.error}@"
                           f"{result.proxy}"
                       ])
                       )

        return id_, len(exists)

    @DefaulConcurrentRepository.locked()
    def mark_success(self, session_id: int, lead_id: int):
        return self._change_status(status=LeadGenResultStatus.SUCCESS,
                            session_id=session_id,
                            lead_id=lead_id)

    @DefaulConcurrentRepository.locked()
    def mark_failed(
            self, session_id: int, lead_id: int,
            error: str = None):
        return self._change_status(status=LeadGenResultStatus.FAILED,
                            session_id=session_id,
                            lead_id=lead_id,
                            error=error)

    @DefaulConcurrentRepository.locked()
    def change_status(
            self, session_id: int,
            lead_id: int,
            status: str,
            sms_code: str = None,
            error: str = None):
        return self._change_status(session_id=session_id,
                            lead_id=lead_id,
                            status=status,
                            sms_code=sms_code,
                            error=error)

    @DefaulConcurrentRepository.locked()
    def can_start_wait_code(self, session_id: int, lead_id: int) -> bool:
        session = self.get(session_id=session_id)

        return self._change_status(status=LeadGenResultStatus.WAIT_CODE,
                            session_id=session_id,
                            lead_id=lead_id)

    @DefaulConcurrentRepository.locked(only_session_id=True)
    def drop_waiting_lead(self, session_id: int):
        self._update_main_lead_status(
            session_id=session_id,
            status=LeadGenResultStatus.FAILED
        )

    @DefaulConcurrentRepository.locked(only_session_id=True)
    def force_new_sms(self, session_id: int):
        self._update_main_lead_status(
            session_id=session_id,
            status=LeadGenResultStatus.RESEND_CODE
        )

    @DefaulConcurrentRepository.locked(only_session_id=True)
    def drop_session(self, session_id: int):
        results = []

        for l in self.get(session_id=session_id):
            results.append(self._change_status(
                session_id=session_id,
                lead_id=l.lead_id,
                status=LeadGenResultStatus.FAILED
            ))

        return all(results)

    def _update_main_lead_status(self, session_id: int,
                                 status: LeadGenResultStatus):
        leads = self.get(session_id=session_id)

        waiting_lead = [l for l in leads if code_is_blocking(status=l.status)]

        if waiting_lead:
            waiting_lead = waiting_lead[0]
        else:
            return False

        return self._change_status(
            status=status,
            session_id=session_id,
            lead_id=waiting_lead.lead_id
        )

    def _change_status(
            self, session_id: int,
            lead_id: int,
            status: str,
            sms_code: str = None,
            error: str = None):
        session = self.get(session_id=session_id)

        if not session:
            return False

        if any([code_is_blocking(l.status)
                for l in session
                if l.lead_id != lead_id]):
            return False

        id_ = f"sessions:session#{session_id}"

        exists = self._conn.get(id_).decode("utf-8").split("&")

        try:
            result = self.get(session_id=session_id, lead_id=lead_id)[0]
        except:
            return

        for i_id, i in enumerate(exists):
            lead_id_raw = i.split("@")[0]

            if lead_id_raw.isdigit() and int(lead_id_raw) == int(lead_id):
                exists[i_id] = (f"{lead_id}@{status}@"
                                f"{sms_code or result.sms_code}@"
                                f"{error or result.error}@{result.proxy}")
                break

        self._conn.set(name=id_,
                       value="&".join(exists))

        return session_id

    def _init_sessions_counter(self):
        self._conn.append("sessions:count", 0)
