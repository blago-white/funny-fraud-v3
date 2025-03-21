from db.leads import LeadGenerationResultsService


class ClientSmsCodesService:
    default_leads_db = LeadGenerationResultsService()

    def __init__(self, leads_db: LeadGenerationResultsService = None):
        self._leads_db = leads_db or self.default_leads_db

    def register_code(self, code: str):
        session_id = self._leads_db.get_count() - 1

        print(f"ADD CLIENT SMS SESSION #{session_id} - '{code}'")

        self._leads_db.send_sms_code(session_id=session_id, sms_code=code)

    def payment_completed(self):
        session_id = self._leads_db.get_count() - 1

        print(f"PAYMENT COMPLETED #{session_id}")

        self._leads_db.set_paid(session_id=session_id)
