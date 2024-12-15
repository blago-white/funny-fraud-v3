import threading
import time

from db.leads import LeadGenerationResultsService
from db.transfer import (LeadGenResult,
                         LeadGenResultStatus)
from parser.profiles.drivers import WebDriversService
from .parser.exceptions import TraficBannedError, InvalidOtpCodeError, OTPError
from .parser.parser import OfferInitializerParser
from .sessions import LeadsGenerationSession
from .utils.sms.services import SmsCodesService
from .exceptions import OtpTimeoutError, ClientAbortedOtpValidation


class LeadsGenerator:
    _data: LeadsGenerationSession = None

    _GLOBAL_RETRIES = 9
    _CARD_DATA_ENTERING_RETRIES = 7

    def __init__(
            self, initializer: OfferInitializerParser = None,
            db_service: LeadGenerationResultsService = None,
            sms_service: SmsCodesService = None,
            drivers_service: WebDriversService = None,
    ):
        self._initializer = initializer or OfferInitializerParser
        self._db_service = db_service or LeadGenerationResultsService()
        self._sms_service = sms_service or SmsCodesService()
        self._drivers_service = drivers_service or WebDriversService()

    def mass_generate(self, data: LeadsGenerationSession):
        new_session_id = self._db_service.get_count()

        self._db_service.init(session_id=new_session_id)

        threads = [threading.Thread(
            target=self.generate,
            args=(new_session_id, LeadsGenerationSession(
                ref_link=data.ref_link,
                proxy=data.proxies[_],
                card=data.card,
                count=1,
            )),
        ) for _ in range(data.count)]

        for t in threads:
            t.start()

        return new_session_id

    def generate(self, session_id: int, session: LeadsGenerationSession):
        _, lead_id = self._db_service.add(
            session_id=session_id,
            result=LeadGenResult(
                session_id=session_id,
                status=LeadGenResultStatus.PROGRESS,
                error="",
            )
        )

        print(f"LEAD #{lead_id} STARTED")

        initializer = self._initializer(
            payments_card=session.card,
            driver=self._drivers_service.get_desctop(
                proxy=session.proxy,
                worker_id=(session_id * lead_id) + 1
            )
        )

        print(f"LEAD #{lead_id} BROWSER INITED")

        for _ in range(self._GLOBAL_RETRIES):
            self._check_stopped(initializer, session_id, lead_id)

            try:
                phone_id, phone = self._sms_service.get_number()

                print(f"LEAD #{lead_id} PHONE RECEIVED")

                initializer.init(
                    url=session.ref_link,
                    phone=phone
                )

                print(f"LEAD #{lead_id} WAIT CODE")

                code = self._receive_sms_code(phone_id=phone_id)

                print(f"LEAD #{lead_id} CODE RECEIVED")

                initializer.enter_registration_code(code=code)

                break
            except TraficBannedError as e:
                print(f"LEAD #{lead_id} TRAFIC BANNED ERROR {repr(e)}")
                self._try_close_driver(initializer=initializer)

                return self._db_service.change_status(
                    status=LeadGenResultStatus.FAILED,
                    session_id=session_id,
                    lead_id=lead_id,
                    error=f"USED PROXY ERROR: {
                        session.proxy.replace("@", "#")
                    }\n{repr(e)}"
                )
            except Exception as e:
                print(f"LEAD #{lead_id} INIT ERROR: {repr(e)} {e}")
                if _ >= self._GLOBAL_RETRIES - 1:
                    self._try_close_driver(initializer=initializer)

                    return self._db_service.change_status(
                        session_id=session_id,
                        lead_id=lead_id,
                        status=LeadGenResultStatus.FAILED,
                        error=str(e)
                    )

        print(f"LEAD #{lead_id} CARD DATA ENTER")

        self._try_enter_card_data(initializer=initializer,
                                  session_id=session_id,
                                  lead_id=lead_id)

        print(f"LEAD #{lead_id} CARD DATA COMPLETE")

        self._wait_for_get_payment_code(session_id=session_id, lead_id=lead_id)

        print(f"LEAD #{lead_id} CAN SUBMIT PAYMENT")

        for _ in range(self._CARD_DATA_ENTERING_RETRIES):
            self._check_stopped(initializer, session_id, lead_id)

            try:
                initializer.submit_payment()

                break
            except Exception as e:
                print(f"LEAD #{lead_id} SUBMIT PAYMENT "
                      f"ERROR: {repr(e)}")

                if _ >= self._CARD_DATA_ENTERING_RETRIES - 1:
                    self._try_close_driver(initializer=initializer)

                    return self._db_service.change_status(
                        session_id=session_id,
                        lead_id=lead_id,
                        status=LeadGenResultStatus.FAILED,
                        error="Failed to send payment request"
                    )

                self._try_enter_card_data(initializer=initializer,
                                          session_id=session_id,
                                          lead_id=lead_id,
                                          retries=1)

                self._db_service.change_status(
                    session_id=session_id,
                    lead_id=lead_id,
                    status=LeadGenResultStatus.WAIT_CODE_FAIL
                )

        print(f"LEAD #{lead_id} SUBMIT PAYMENT")

        self._db_service.change_status(
            session_id=session_id,
            lead_id=lead_id,
            status=LeadGenResultStatus.WAIT_CODE
        )

        for _ in range(3):
            self._check_stopped(initializer, session_id, lead_id)

            try:
                code = self._get_payment_otp(session_id=session_id,
                                             lead_id=lead_id)

                initializer.enter_payment_card_otp(code=code)

                break

            except ClientAbortedOtpValidation as e:
                print(f"LEAD #{lead_id} OTP VERIF CANCELED {repr(e)}")
                return self._try_close_driver(initializer=initializer)

            except (Exception, InvalidOtpCodeError, OtpTimeoutError) as e:
                if type(e) is OtpTimeoutError:
                    print(f"LEAD #{lead_id} OTP TIMEOUT ERROR: {repr(e)}")
                else:
                    print(f"LEAD #{lead_id} ENTER PAYMENT OTP ERROR: {repr(e)}")

                if _ >= 2:
                    error_msg = ("Otp waiting timeout"
                                 if type(e) is OtpTimeoutError else
                                 "Failed to receive otp or enter otp code")

                    error_msg += " [Otp code retries 3]"

                    self._try_close_driver(initializer=initializer)
                    return self._db_service.change_status(
                        status=LeadGenResultStatus.FAILED,
                        session_id=session_id,
                        lead_id=lead_id,
                        error=error_msg
                    )

            print(f"LEAD #{lead_id} INVALID OTP, RETRY")

            self._db_service.change_status(
                status=LeadGenResultStatus.CODE_INVALID,
                session_id=session_id,
                lead_id=lead_id,
            )

            initializer.resend_otp()

        self._try_close_driver(initializer=initializer)

        print(f"LEAD #{lead_id} FINISHED")

        self._db_service.change_status(
            status=LeadGenResultStatus.SUCCESS,
            session_id=session_id,
            lead_id=lead_id,
        )

    def _receive_sms_code(self, phone_id: int):
        code, start_time = None, time.time()

        while code is None:
            if time.time() - start_time > 90:
                raise TimeoutError("No receive sms")

            code = self._sms_service.check_code(phone_id=phone_id)

            time.sleep(1)

        return code

    def _get_payment_otp(self, session_id: int, lead_id: int):
        START = time.time()
        sms_code = self._db_service.get(session_id=session_id,
                                        lead_id=lead_id)[0].sms_code
        USE_FORCE = False

        while time.time() - START < 120:
            print(f"LEAD {lead_id} REFRESH OTP {self._db_service.get(
                session_id=session_id,
                lead_id=lead_id
            )}")
            lead = self._db_service.get(
                session_id=session_id,
                lead_id=lead_id
            )[0]

            if lead.status == LeadGenResultStatus.FAILED:
                raise ClientAbortedOtpValidation("Status FAILED set")

            if lead.status == LeadGenResultStatus.RESEND_CODE:
                USE_FORCE = True

            if (time.time() - START > 30) and USE_FORCE:
                raise OtpTimeoutError("Forced new code")

            if ((lead.sms_code != sms_code) and
                    lead.sms_code and
                    lead.sms_code.isdigit()):
                print(f"OTP LOADED {lead_id} - {lead.sms_code}")
                return lead.sms_code

            sms_code = lead.sms_code

            time.sleep(.5)

        raise OtpTimeoutError("Client otp timeout")

    def _wait_for_get_payment_code(self, session_id: int, lead_id: int):
        START = time.time()

        while time.time() - START < 60 * 60 * 3:

            if self._db_service.can_start_wait_code(
                    session_id=session_id,
                    lead_id=lead_id
            ):
                print(f"LEAD #{lead_id} CAN GET SMS")
                return True

            time.sleep(.5)

    def _try_enter_card_data(
            self, initializer: OfferInitializerParser,
            session_id: int,
            lead_id: int,
            retries: int = 0):
        for _ in range(retries or self._CARD_DATA_ENTERING_RETRIES):
            self._check_stopped(initializer, session_id, lead_id)
            try:
                initializer.enter_card_data()

                break
            except Exception as e:
                print(f"ENTER CARD DATA ERROR: {repr(e)}")
                if _ >= (retries or self._CARD_DATA_ENTERING_RETRIES) - 1:
                    return self._db_service.change_status(
                        session_id=session_id,
                        lead_id=lead_id,
                        status=LeadGenResultStatus.FAILED,
                        error="Failed to enter card data"
                    )

    def _try_close_driver(self, initializer: OfferInitializerParser):
        try:
            initializer.driver.close()
        except:
            pass

    def _check_stopped(self, initializer: OfferInitializerParser,
                       session_id: int, lead_id: int):
        if self._db_service.get(
                session_id=session_id, lead_id=lead_id
        )[0].status == LeadGenResultStatus.FAILED:
            initializer.driver.close()
            raise SystemExit(0)
