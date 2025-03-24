import threading
import time

from db.sms import LatestMobileSmsTextService, LatestSmsTypes
from db.leads import LeadGenerationResultsService, LeadGenResultStatus


def _d(time_const: int):
    return time.time() - time_const


class SessionSupervisor:
    _session_id: int
    _timeout: int

    _stopped: bool = False
    _is_runned = False

    default_leads_db_service = LeadGenerationResultsService
    default_latest_sms_service = LatestMobileSmsTextService

    def __init__(
            self, session_id: int,
            leads_db: LeadGenerationResultsService = None,
            timeout: int = 60 * 60,
            latest_sms_service: LatestMobileSmsTextService = None):
        self._session_id = session_id
        self._timeout = timeout

        self._leadsdb = (leads_db or self.default_leads_db_service)()
        self._latest_codes_service = latest_sms_service or self.default_latest_sms_service

    @property
    def is_active(self):
        return not self._stopped

    @property
    def _can_create_supervisor(self):
        result = not self._is_runned

        if result:
            self._is_runned = True

        return result

    def supervise_session(self):
        if not self._can_create_supervisor:
            raise PermissionError("Manager Already Running")

        supervisor_th = threading.Thread(target=self._supervise_session)
        supervisor_th.start()

    def _supervise_session(self):
        self._t_last_success_lead = 0

        self._START_TIME = time.time()

        self._t_target_lead_status_changed = 0
        self._target_lead_id = self.target_lead = None
        self._target_lead_statuses_history = []

        while (self._timeout > _d(self._START_TIME) and
               self._leadsdb.get_count() - 1 == self._session_id):
            self._leads: list[LeadGenResult] = self._leadsdb.get(
                session_id=self._session_id
            ) or []

            if len([l for l in self._leads if l.status in [
                LeadGenResultStatus.SUCCESS, LeadGenResultStatus.FAILED
            ]]) == len(self._leads):
                break

            self._process_target_lead()

            self._process_session_dropping_events()

            self._process_local_leads_events()

            time.sleep(.5)

        print(f"MANAGER OF SID: {self._session_id} KILLED!")

    def _process_target_lead(self):
        if self._target_lead_id:
            try:
                self.target_lead = [
                    l for l in self._leads if l.lead_id == self._target_lead_id
                ].pop()
            except:
                pass

        if self.target_lead:
            if not self._target_lead_statuses_history:
                self._target_lead_statuses_history.append(
                    self.target_lead.status
                )

            if self._target_lead_statuses_history[-1] != self.target_lead.status:
                self._target_lead_statuses_history.append(
                    self.target_lead.status
                )

            self._t_target_lead_status_changed = time.time()

    def _process_local_leads_events(self):
        self.target_lead = None

        if self.target_lead.status == LeadGenResultStatus.WAIT_CODE_FAIL:
            if _d(self._t_target_lead_status_changed) > 60:
                print("MANAGER: WAIT CODE FAIL: DROP WAITING LEAD [1]")

                self._leadsdb.drop_waiting_lead(session_id=self._session_id)

            if (self._target_lead_statuses_history[-2] ==
                    LeadGenResultStatus.CODE_RECEIVED):
                print("MANAGER: WAIT CODE FAIL: DROP WAITING LEAD [2]")

                self._leadsdb.drop_waiting_lead(session_id=self._session_id)

        if self.target_lead.status == LeadGenResultStatus.WAIT_CODE:
            if (
                    _d(self._t_target_lead_status_changed) >= 20
            ) or (
                self._target_lead_statuses_history[-2] == LeadGenResultStatus.CODE_RECEIVED
            ):
                print("MANAGER: WAIT CODE: WAIT CODE AFTER 20 SEC. OR CODE RECEIVED PREVIOUS CODE!")

                latest_sms_type, latest_sms = self._latest_codes_service.get()

                if latest_sms_type == LatestSmsTypes.CODE:
                    print("MANAGER: WAIT CODE: SEND FORGOTTEN SMS CODE!")

                    self._leadsdb.send_sms_code(
                        session_id=self._session_id, sms_code=latest_sms
                    )

            if _d(self._t_target_lead_status_changed) > 3 * 60:
                print("MANAGER: WAIT CODE: WAIT CODE AFTER 180 SEC. DROP LEAD!")

                self._leadsdb.drop_waiting_lead(session_id=self._session_id)

        if self.target_lead.status == LeadGenResultStatus.CODE_RECEIVED and _d(
                self._t_target_lead_status_changed
        ) >= 30:
            print("MANAGER: CODE RECEIVED: NOT CHANGING 30 SEC.")

            if self._latest_codes_service.get()[0] == LatestSmsTypes.PAYMENT:
                print("MANAGER: CODE RECEIVED: SET PAID")

                self._leadsdb.set_paid(session_id=self._session_id)
            else:
                print("MANAGER: CODE RECEIVED: DROP LEAD")

                self._leadsdb.drop_waiting_lead(session_id=self._session_id)

    def _process_session_dropping_events(self):
        completed, failed, progress = (
            [l for l in self._leads if l.status == LeadGenResultStatus.SUCCESS],
            [l for l in self._leads if l.status == LeadGenResultStatus.FAILED],
            [l for l in self._leads if l.status == LeadGenResultStatus.PROGRESS]
        )

        if (
                _d(self._START_TIME) <= 90 and len(failed) >= (len(self._leads) * (1/3)) or
                _d(self._START_TIME) <= 20 and len(failed) >= (len(self._leads) * (1/6))
        ):
            for f in failed:
                if ("navigator" in f.error.lower()) or (
                        "gologin" in f.error.lower()):
                    print("MANAGER: SESSION: MANY ERRORS ON START - DROPPED")

                    self._leadsdb.drop_session(session_id=self._session_id)

        if _d(self._START_TIME) >= 60 * 10 and not len(completed):
            error_msgs = "".join([l.error for l in failed])

            if (("navigator" in error_msgs.lower()) or
                    ("gologin" in error_msgs.lower())):
                print("MANAGER: SESSION: NOT FOUND SUCCESSED LEADS AFTER 10 MINS.")

                self._leadsdb.drop_session(session_id=self._session_id)

            if ("sms" not in error_msgs.lower() and
                    len(failed) >= max(2, len(self._leads) * .1)):
                print("MANAGER: SESSION: NOT FOUND SMS WORD IN ERROR MESSAGES")

                self._leadsdb.drop_session(session_id=self._session_id)

        if _d(self._START_TIME) >= (60 * 13) and not len(completed):
            print("MANAGER: SESSION: NOT COMPLETED AFTER 13 MINS")

            self._leadsdb.drop_session(session_id=self._session_id)

        if len(failed) > (len(self._leads) * .6):
            print("MANAGER: SESSION: TOO MANY FAILED")

            self._leadsdb.drop_session(session_id=self._session_id)

        if (_d(self._t_last_success_lead) > (8 * 60) and
                len(progress) <= (len(self._leads) * .2)):
            print("MANAGER: SESSION: TOO MANY TIME LEFT [1]")

            self._leadsdb.drop_session(session_id=self._session_id)

        if (_d(self._t_last_success_lead) > (4 * 60) and
                len(progress) <= (len(self._leads) * .15)):
            print("MANAGER: SESSION: TOO MANY TIME LEFT [2]")

            self._leadsdb.drop_session(session_id=self._session_id)

        if _d(self._t_last_success_lead) > 11 * 60:
            print("MANAGER: SESSION: TOO MANY TIME LEFT [3]")

            self._leadsdb.drop_session(session_id=self._session_id)
