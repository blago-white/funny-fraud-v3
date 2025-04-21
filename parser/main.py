import threading
import time

from db.leads import LeadGenerationResultsService
from db.transfer import (LeadGenResult,
                         LeadGenResultStatus)
from db.proxy import ProxyRepository
from parser.profiles.drivers import WebDriversService
from .parser.exceptions import (TraficBannedError,
                                InvalidOtpCodeError,
                                OTPError,
                                BadPhoneError,
                                RegistrationSMSTimeoutError,
                                BadSMSService,
                                InitializingError,
                                CardDataEnteringBanned)
from .parser.parser import OfferInitializerParser
from .sessions import LeadsGenerationSession, SessionStrategy
from .utils.sms.elsms import ElSmsSMSCodesService
from .utils.sms.middleware.throttling import SmsServiceThrottlingMiddleware
from .utils.sessions import session_results_commiter
from .exceptions import OtpTimeoutError, ClientAbortedOtpValidation, \
    CreatePaymentFatalError


class LeadsGenerator:
    _data: LeadsGenerationSession = None

    _GLOBAL_RETRIES = 9
    _CARD_DATA_ENTERING_RETRIES = 7
    _PHONE_RETRIEVING_RETRIES = 4
    _SMS_SENDING_INITIALIZING_RETRIES = 3

    def __init__(
            self, initializer: OfferInitializerParser = None,
            db_service: LeadGenerationResultsService = None,
            sms_service: ElSmsSMSCodesService = None,
            drivers_service: WebDriversService = None,
            proxy_service: ProxyRepository = None
    ):
        self._initializer = initializer or OfferInitializerParser
        self._db_service = db_service or LeadGenerationResultsService()
        self._proxy_service = proxy_service or ProxyRepository()
        self._sms_service = sms_service or ElSmsSMSCodesService()
        self._drivers_service = drivers_service or WebDriversService()

    def mass_generate(self, data: LeadsGenerationSession):
        print(self._sms_service, "SMS SERVICE")

        new_session_id = self._db_service.get_count()

        self._db_service.init(session_id=new_session_id)

        threads = []

        SmsServiceThrottlingMiddleware.clean_buffer()

        for ref_link in data.ref_links:
            threads.extend([threading.Thread(
                target=self.generate,
                kwargs=dict(
                    session_id=new_session_id,
                    session=LeadsGenerationSession(
                        ref_link=ref_link,
                        card=data.card,
                        count=1,
                    )),
            ) for _ in range(data.count)])

        for t in threads:
            t.start()

        return new_session_id

    @session_results_commiter
    def generate(
            self, session_id: int,
            lead_id: int,
            initializer: OfferInitializerParser,
            session: LeadsGenerationSession,
            use_phone: list[int, str] = (None, None)):
        if len(use_phone) != 2:
            use_phone = [None, None]

        self._check_stopped_with_phone(session_id, lead_id, phone_id=use_phone[0])

        bad_phone = False

        for _ in range(self._GLOBAL_RETRIES):
            self._check_stopped_with_phone(session_id, lead_id, phone_id=use_phone[0])

            for _ in range(self._PHONE_RETRIEVING_RETRIES):
                self._check_stopped_with_phone(session_id, lead_id, phone_id=use_phone[0])

                if bad_phone and use_phone:
                    self._sms_service.cancel(phone_id=use_phone[0])

                use_phone = self._try_get_phone(
                    exists_phone=use_phone if not bad_phone else (None, None),
                    lead_id=lead_id
                )

                if not all(use_phone):
                    continue
                else:
                    phone_id, phone = use_phone
                    bad_phone = False
                    break
            else:
                raise BadSMSService(
                    f"Bad response from sms service "
                    f"[{self._PHONE_RETRIEVING_RETRIES} retry]!"
                )

            print(f"LEAD #{lead_id} PHONE RECEIVED - {phone_id=} {phone=}")

            for _ in range(self._SMS_SENDING_INITIALIZING_RETRIES):
                if bad_phone:
                    break

                self._check_stopped_with_phone(session_id, lead_id, phone_id=phone_id)

                try:
                    if session.strategy == SessionStrategy.DEFAULT:
                        initializer.init(
                            url=session.ref_link,
                            phone=phone
                        )
                    elif session.strategy == SessionStrategy.SBER_ID:
                        initializer.init_sber_id(phone=phone)

                    break
                except BadPhoneError:
                    print(f"LEAD #{lead_id} CANNOT USE PHONE TO REG")

                    bad_phone = True
                    continue
                except TraficBannedError:
                    raise TraficBannedError(
                        used_phone_id=phone_id,
                        used_phone_number=phone
                    )
                except Exception as e:
                    print(f"LEAD #{lead_id} CANNOT SEND REG SMS RETRY №{_}")
                    continue
            else:
                if bad_phone:
                    continue

                raise InitializingError(
                    used_phone_id=phone_id,
                    used_phone_number=phone
                )

            self._check_stopped_with_phone(session_id, lead_id, phone_id=phone_id)

            try:
                print(f"LEAD #{lead_id} WAIT CODE")

                code = self._receive_sms_code(phone_id=phone_id)

                print(f"LEAD #{lead_id} CODE RECEIVED")

                initializer.enter_registration_code(code=code)

                break
            except (RegistrationSMSTimeoutError, CardDataEnteringBanned):
                bad_phone = True

                self._sms_service.cancel(phone_id=phone_id)

                if _ >= self._GLOBAL_RETRIES - 1:
                    raise BadPhoneError(
                        used_phone_id=phone_id,
                        used_phone_number=phone
                    )

                continue

            except TraficBannedError as e:
                print(f"LEAD #{lead_id} TRAFIC BANNED ERROR {repr(e)}")

                self._sms_service.cancel(phone_id=phone_id)

                raise TraficBannedError(
                    used_phone_id=phone_id,
                    used_phone_number=phone
                )
            except Exception as e:
                self._sms_service.cancel(phone_id=phone_id)

                print(f"LEAD #{lead_id} INIT ERROR: {repr(e)} {e}")
                if _ >= self._GLOBAL_RETRIES - 1:
                    raise InitializingError(
                        crude_exception=e,
                        used_phone_id=None,
                        used_phone_number=None
                    )
                bad_phone = True
        else:
            raise InitializingError(
                used_phone_id=None,
                used_phone_number=None
            )

        print(f"LEAD #{lead_id} CARD DATA ENTER")

        if session.strategy == SessionStrategy.SBER_ID:
            self._initializer.open_logined_sber_ref_link(url=session.ref_link)

        try:
            self._try_enter_card_data(initializer=initializer,
                                      session_id=session_id,
                                      lead_id=lead_id)
        except:
            raise CreatePaymentFatalError("Cannot set card data!")

        print(f"LEAD #{lead_id} CARD DATA COMPLETE")

        self._wait_for_get_payment_code(session_id=session_id, lead_id=lead_id)

        print(f"LEAD #{lead_id} CAN SUBMIT PAYMENT")

        for _ in range(self._CARD_DATA_ENTERING_RETRIES):
            self._check_stopped(session_id, lead_id)

            try:
                initializer.submit_payment()

                break
            except Exception as e:
                self._db_service.change_status(
                    session_id=session_id,
                    lead_id=lead_id,
                    status=LeadGenResultStatus.WAIT_CODE_FAIL
                )

                print(f"LEAD #{lead_id} SUBMIT PAYMENT "
                      f"ERROR: {repr(e)}")

                if _ >= self._CARD_DATA_ENTERING_RETRIES - 1:
                    raise CreatePaymentFatalError(
                        "Failed to send payment request"
                    )

                try:
                    self._try_enter_card_data(initializer=initializer,
                                              session_id=session_id,
                                              lead_id=lead_id,
                                              retries=1)
                except:
                    pass

        print(f"LEAD #{lead_id} SUBMIT PAYMENT")

        self._db_service.change_status(
            session_id=session_id,
            lead_id=lead_id,
            status=LeadGenResultStatus.WAIT_CODE
        )

        for _ in range(3):
            self._check_stopped(session_id, lead_id)

            try:
                self._check_paid(session_id, lead_id)
            except SystemExit:
                break

            code = None

            try:
                code = self._get_payment_otp(session_id=session_id,
                                             lead_id=lead_id,
                                             prev_code=code,
                                             is_retry=_ != 0)

                initializer.enter_payment_card_otp(code=code)

                break
            except ClientAbortedOtpValidation as e:
                print(f"LEAD #{lead_id} OTP VERIF CANCELED {repr(e)}")
                raise e
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

                    raise CreatePaymentFatalError(error_msg)

            print(f"LEAD #{lead_id} INVALID OTP, RETRY")

            self._db_service.change_status(
                status=LeadGenResultStatus.CODE_INVALID,
                session_id=session_id,
                lead_id=lead_id,
            )

            initializer.resend_otp()

        print(f"LEAD #{lead_id} FINISHED")

    def _receive_sms_code(self, phone_id: int):
        code, start_time = None, time.time()

        while code is None:
            if time.time() - start_time > self._sms_service.SMS_TIMEOUT:
                self._sms_service.cancel(phone_id=phone_id)

                time.sleep(1)

                after_cancel_code = self._sms_service.check_code(phone_id=phone_id)

                if after_cancel_code is not None:
                    return after_cancel_code

                raise RegistrationSMSTimeoutError("No receive sms")

            code = self._sms_service.check_code(phone_id=phone_id)

            time.sleep(1)

        print(f"CODE: {code}")

        return code

    def _get_payment_otp(
            self, session_id: int,
            lead_id: int,
            prev_code: str = None,
            is_retry: bool = False):
        START = time.time()

        if is_retry:
            sms_code = prev_code or self._db_service.get(
                session_id=session_id,
                lead_id=lead_id
            )[0].sms_code
        else:
            sms_code = "None"

        USE_FORCE = False

        while time.time() - START < 120:
            lead = self._db_service.get(
                session_id=session_id,
                lead_id=lead_id
            )[0]

            print(f"LEAD {lead_id} REFRESH OTP : {sms_code} - {lead.sms_code}")

            if lead.status in (LeadGenResultStatus.FAILED, LeadGenResultStatus.PROGRESS):
                raise ClientAbortedOtpValidation("Status FAILED set")

            if lead.status == LeadGenResultStatus.RESEND_CODE:
                USE_FORCE = True

            if ((time.time() - START) > 30) and USE_FORCE:
                raise OtpTimeoutError("Forced new code")

            if ((lead.sms_code != sms_code) and
                lead.sms_code and
                lead.sms_code.isdigit()) or (
                    lead.status == LeadGenResultStatus.CODE_RECEIVED
            ):
                print(f"OTP LOADED {lead_id} - {lead.sms_code}")
                return lead.sms_code

            sms_code = lead.sms_code

            time.sleep(.5)

        if sms_code != "None":
            return sms_code

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
            self._check_stopped(session_id, lead_id)
            try:
                initializer.enter_card_data()

                break
            except Exception as e:
                print(f"ENTER CARD DATA ERROR: {repr(e)}")
                if _ >= (retries or self._CARD_DATA_ENTERING_RETRIES) - 1:
                    raise type(e)("Failed to enter card data")

    def _try_close_driver(self, initializer: OfferInitializerParser):
        try:
            initializer.driver.close()
        except:
            pass

    def _check_stopped_with_phone(self, *args, phone_id: int = None, **kwargs):
        try:
            self._check_stopped(*args, **kwargs)
        except SystemExit as e:
            self._sms_service.cancel(phone_id=phone_id)
            raise e

    def _check_stopped(
            self, session_id: int, lead_id: int):
        if self._db_service.get(
            session_id=session_id, lead_id=lead_id
        )[0].status == LeadGenResultStatus.FAILED:
            raise SystemExit(0)

    def _check_paid(self, session_id: int, lead_id: int):
        if self._db_service.get(
            session_id=session_id, lead_id=lead_id
        )[0].status == LeadGenResultStatus.SUCCESS:
            raise SystemExit(0)

    def _try_get_phone(self, exists_phone: tuple[int, str],
                       lead_id: int) -> tuple[int, str]:
        try:
            if not all(exists_phone):
                exists_phone = self._sms_service.get_number()

                print(f"LEAD #{lead_id} PHONE GENERATED")
        except Exception as e:
            print(e)
            print(f"LEAD #{lead_id} CANNOT GET PHONE NUMBER")
            return None, None
        else:
            return exists_phone
