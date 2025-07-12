from db.leads import LeadGenerationResultsService
from db.sms import LatestMobileSmsTextService


class ClientSmsCodesService:
    default_leads_db = LeadGenerationResultsService()
    default_codes_db = LatestMobileSmsTextService()

    def __init__(self, leads_db: LeadGenerationResultsService = None,
                 codes_db: LatestMobileSmsTextService = None):
        self._leads_db = leads_db or self.default_leads_db
        self._codes_db = codes_db or self.default_codes_db

    def register_code(self, code: str):
        session_id = self._leads_db.get_count() - 1

        print(f"ADD CLIENT SMS SESSION #{session_id} - '{code}'")

        self._leads_db.send_sms_code(session_id=session_id, sms_code=code)

        self._codes_db.add(text=code)

    def payment_completed(self):
        session_id = self._leads_db.get_count() - 1

        print(f"PAYMENT COMPLETED #{session_id}")

        self._leads_db.set_paid(session_id=session_id)

        self._codes_db.add(True)
