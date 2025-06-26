import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire.webdriver import Chrome

from . import utils, exceptions


class OfferInitializerParser:
    _form_already_inited: bool = False
    _card_data_already_entered: bool = False
    _card_data_page_path: str = None
    _account_not_logined: bool = None

    _OWNER_DATA_FIELDS_IDS = [
        "input[name='firstName']",
        "input[name='lastName']",
        "input[name='dob']",
        "input[name='password']",
        "input[name='confirmPassword']",
        "input[name='email']",
    ]

    _PAYMENT_CARD_FIELDS_IDS = [
        "input[id='pan']",
        "input[id='expiry']",
        "input[id='cvc']"
    ]

    def __init__(
            self, payments_card: utils.PaymentsCardData,
            driver: Chrome,
            owner_data_generator: utils.OwnerCredentalsGenerator = None):
        self._driver = driver
        self._payments_card = payments_card

        if type(payments_card) is str:
            self._payments_card = utils.PaymentsCardData.generate(
                self._payments_card
            )

        self._owner_data_generator = (owner_data_generator or
                                      utils.OwnerCredentalsGenerator())

    @property
    def driver(self):
        return self._driver

    def init(self, url: str, phone: str, _retry: bool = False):
        if not self._form_already_inited:
            self._driver.get(url=url)

            self._click_get_account()

            self._form_already_inited = True
        else:
            try:
                self._try_drop_form()
            except:
                self._form_already_inited = False

                return self.init(url=url, phone=phone)

        try:
            self._enter_phone(phone=phone)
        except Exception as e:
            self._form_already_inited = False

            if not _retry:
                return self.init(url=url, phone=phone, _retry=True)

            raise e

    def init_sber_id(self, phone: str, _retry: bool = False):
        self._driver.get(
            url="https://id.sber.ru/profile/me?utm_medium=referral&utm_source=sberbank_ru&utm_campaign=button_create_sberid"
        )

        self._form_already_inited = True

        try:
            self._enter_phone(phone=phone)
        except Exception as e:
            self._form_already_inited = False

            if not _retry:
                return self.init_sber_id(phone=phone, _retry=True)

            raise e

    def test_proxy_trafic_for_sberprime(self, url: str):
        self._driver.get(url=url)

        self._click_get_account()

    def open_logined_sber_ref_link(self, url: str):
        self._driver.get(url=url)

        try:
            WebDriverWait(self._driver, 40).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[id='pan']")
                )
            )
        except:
            self._click_get_account()

            WebDriverWait(self._driver, 50).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[id='pan']")
                )
            )

    def submit_payment(self):
        self._submit_payment_form()

    def enter_registration_code(self, code: str):
        self._enter_registration_code(code=code)

        self._check_registration_code_correct()

        self._enter_owner_data()

    def enter_payment_card_otp(self, code: str):
        WebDriverWait(self._driver, 60).until(
            expected_conditions.presence_of_element_located(
                (By.ID, "passwordEdit")
            )
        )

        self._driver.find_element(
            By.ID, "passwordEdit"
        ).click()

        self._driver.find_element(
            By.ID, "passwordEdit"
        ).send_keys(code)

        try:
            WebDriverWait(self._driver, 7).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[class='error']")
                )
            )
        except:
            for _ in range(3):
                try:
                    for _ in range(35):
                        if (("подписка" in self._driver.page_source.lower())
                                and (
                                        "оформлена" in self._driver.page_source.lower())):
                            print("CONFIRM WORDS IN PAGE SOURCE")
                            return True

                        if "no_spasibo_registration" in self._driver.current_url:
                            print("CONFIRM ARGUMENT IN URL")
                            return True

                        try:
                            WebDriverWait(self._driver, 1).until(
                                expected_conditions.presence_of_element_located(
                                    (By.CSS_SELECTOR, "p[class='css-dth2xi']")
                                )
                            )
                            print("CONFIRM BUTTON EXISTS")
                            return True
                        except:
                            print(
                                f"NEXT CYCLE CONFIRMATION: {"no_spasibo_registration" in self._driver.current_url} {self._driver.current_url}")
                            continue
                    raise TimeoutError("Cannot find success flags")
                except:
                    self._driver.execute_script(
                        "location.href = location.href;")
            else:
                raise exceptions.OTPError(
                    "Success page not opened but code is ok")

        raise exceptions.InvalidOtpCodeError("Invalid otp code received")

    def enter_card_data(self):
        if self._card_data_already_entered:
            if self._card_data_page_path:
                self._driver.get(self._card_data_page_path)
            else:
                self._driver.execute_script(
                    f"location.href = location.href"
                )
        else:
            self._try_go_to_payment()

        self._card_data_already_entered = True

        for _ in range(4):
            try:
                self._enter_card()
                return
            except:
                try:
                    self._click_subscription_button()
                except:
                    pass

                if self._card_data_already_entered:
                    self._driver.get(self._card_data_page_path)
                else:
                    self._driver.execute_script(
                        f"location.href = location.href"
                    )
        raise Exception("Cannot enter card!")

    def resend_otp(self):
        try:
            WebDriverWait(self._driver, 10).until(
                expected_conditions.element_to_be_clickable(
                    (By.ID, "resendLink")
                )
            )

            self._driver.find_element(
                By.ID, "resendLink"
            ).click()
        except:
            print("CANNOT RESEND CODE")

    def _enter_card(
            self, is_retry: bool = False, overrided_timeout: int = 120):
        WebDriverWait(self._driver, overrided_timeout).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "input[id='pan']")
            )
        )

        # if not is_retry:
            # self._try_exit_profile(override_timeout=.25)

        # if is_retry:
        #     if self._payments_card.number in self._driver.find_element(
        #         By.CSS_SELECTOR,
        #         self._PAYMENT_CARD_FIELDS_IDS[0]
        #     ).text:
        #

        for field_id, field_value in zip(self._PAYMENT_CARD_FIELDS_IDS,
                                         (self._payments_card.number,
                                          self._payments_card.date,
                                          self._payments_card.cvc)):
            field = self._driver.find_element(
                By.CSS_SELECTOR, field_id
            )

            field.click()

            field.send_keys(Keys.CONTROL + "a")
            field.send_keys(Keys.DELETE)

            field.send_keys(field_value)

    def _submit_payment_form(
            self, _need_reenter_card: bool = False,
            _reenter_card_optional: bool = False,
            _need_click_submit: bool = True,
            _retry_count: int = 6):
        if not _retry_count:
            self._card_data_already_entered = False

            print("ERROR GETTING OTP CODE PAGE")

            raise exceptions.OTPError("Error getting otp page")

        print(
            f"CALL _submit_payment_form({_need_click_submit=}, {_need_reenter_card=})")

        if _need_reenter_card:
            self._card_data_already_entered = False

            try:
                self._enter_card(overrided_timeout=15)
            except:
                raise Exception("Cannot submit, maybe sub page opens!")

        try:
            if _need_click_submit:
                self._click_submit_payment_form()
            else:
                self._click_submit_payment_form(override_timeout=3)
        except:
            pass

        print("WAIT FOR OTP PASSWORD")

        if _need_click_submit:
            START = time.time()

            while True:
                if "Не удалось инициализировать" in self._driver.page_source:
                    self._driver.execute_script(
                        "location.href = location.href;")

                    return self._submit_payment_form(
                        _need_reenter_card=True,
                        _retry_count=_retry_count - 1
                    )

                elif "Сервис недоступен" in self._driver.page_source:
                    self._driver.execute_script(
                        "location.href = location.href;")

                    return self._submit_payment_form(
                        _need_reenter_card=True,
                        _retry_count=_retry_count - 1
                    )

                if time.time() - START > 19:
                    print("PAYMENT URL DONT CHANGES")

                    raise Exception("Cannot submit form")

                if self._driver.current_url != self._card_data_page_path:
                    break

                try:
                    self._enter_card(overrided_timeout=2)
                except:
                    pass

                try:
                    self._click_submit_payment_form(override_timeout=2)
                except:
                    pass

            print("PAYMENT URL CHANGES")

        try:
            WebDriverWait(self._driver, 15).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "passwordEdit")
                )
            )

            print("OTP PASSWORD REQUEST COMPLETE")

            return
        except:
            print("OTP PASSWORDS FIELD FIND ERROR 1")

            try:
                if not (self._driver.current_url.endswith("payment/") or self._driver.current_url.endswith("payment")):
                    raise Exception("Is not sub page, skip!")

                self._click_subscription_button()

                print("CLICK GET SUB №1 | REENTER CARD")

                return self._submit_payment_form(
                    _need_reenter_card=True,
                    _retry_count=_retry_count - 1
                )
            except:
                print("CANNOT CLICK GET SUB №1")

                if "не удалось инициализировать" in self._driver.page_source.lower():
                    print("RED CROSS EXISTS")

                    self._driver.execute_script(
                        "location.href = location.href;"
                    )
                    return self._submit_payment_form(
                        _need_click_submit=False,
                        _retry_count=_retry_count - 1
                    )

        try:
            WebDriverWait(self._driver, 13).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "passwordEdit")
                )
            )

            print("OTP PASSWORD REQUEST COMPLETE")

            return
        except:
            try:
                if not (self._driver.current_url.endswith("payment/") or self._driver.current_url.endswith("payment")):
                    raise Exception("Is not sub page, skip!")

                self._click_subscription_button()

                print("CLICK GET SUB №2 | REENTER CARD")

                return self._submit_payment_form(
                    _need_reenter_card=True,
                    _retry_count=_retry_count - 1
                )
            except:
                self._click_subscription_button()

                print("CANNOT CLICK GET SUB №2 | NEED RETRY")

        self._driver.execute_script("location.href = location.href;")
        time.sleep(1)

        return self._submit_payment_form(_need_click_submit=False,
                                         _retry_count=_retry_count - 1)

    def _try_go_to_payment(self):
        pass
        # try:
        #     WebDriverWait(
        #         self._driver, 60
        #     ).until(
        #         expected_conditions.presence_of_element_located(
        #             (By.CSS_SELECTOR, "input[data-testid='redirectToServiceBtn']")
        #         )
        #     )
        #
        #     self._driver.find_element(
        #         By.CSS_SELECTOR, "input[data-testid='redirectToServiceBtn']"
        #     ).click()
        # except:
        #     pass

    def _enter_owner_data(self):
        for field_id, field_data in zip(
                self._OWNER_DATA_FIELDS_IDS,
                self._owner_data_generator.get_random_owner_data()
        ):
            field = self._driver.find_element(
                By.CSS_SELECTOR, field_id
            )

            field.click()
            field.send_keys(field_data)

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='submitFormButton']"
        ).click()

    def _check_registration_code_correct(self):
        try:
            WebDriverWait(self._driver, 10).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, self._OWNER_DATA_FIELDS_IDS[0])
                )
            )
        except:
            raise exceptions.CardDataEnteringBanned(
                "Cannot enter card data!"
            )

    def _enter_registration_code(self, code: str):
        WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='sms0']")
            )
        )

        for i in range(5):
            self._driver.find_element(
                By.CSS_SELECTOR, f"input[name='sms{i}']"
            ).send_keys(code[i])

    def _enter_phone(self, phone: str):
        try:
            WebDriverWait(self._driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='tel']")
                )
            )
        except:
            phone_input = self._driver.find_element(
                By.CSS_SELECTOR, "input[data-testid='phoneNumber-input']"
            )
        else:
            phone_input = self._driver.find_element(
                By.CSS_SELECTOR, "input[type='tel']"
            )

        phone_input.click()

        phone_input.send_keys(phone[1:])

        WebDriverWait(self._driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "button[data-testid='phoneNumber-nextButton']")
            )
        )

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='phoneNumber-nextButton']"
        ).click()

        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.text_to_be_present_in_element(
                    locator="body",
                    text_="Продолжить вход с этим номером пока не можем"
                )
            )
        except:
            pass
        else:
            raise exceptions.BadPhoneError()
        finally:
            if "Продолжить вход с этим номером пока не можем".lower() in self._driver.page_source.lower():
                raise exceptions.BadPhoneError()

        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "inputError")
                )
            )
        except:
            pass
        else:
            raise exceptions.BadPhoneError()

        try:
            WebDriverWait(self._driver, 10).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "button[data-testid='reinitSessionButton']")
                )
            )
        except:
            return


        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='reinitSessionButton']"
        ).click()

        raise ValueError

    def _click_get_account(self):
        try:
            WebDriverWait(self._driver, 40).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".css-1tb3n43.e1jyzd9p2")
                )
            )
        except:
            raise exceptions.TraficBannedError()

        self._driver.find_element(
            By.CSS_SELECTOR, ".css-1tb3n43.e1jyzd9p2"
        ).click()

    def _try_drop_form(self):
        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "button[data-testid='topBarLeftBtn']")
                )
            )
            back_btn = self._driver.find_element(
                By.CSS_SELECTOR, "button[data-testid='topBarLeftBtn']"
            )

            back_btn.click()

            WebDriverWait(self._driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "button[data-testid='topBarLeftBtn']")
                )
            )

            back_btn = self._driver.find_element(
                By.CSS_SELECTOR, "button[data-testid='topBarLeftBtn']"
            )

            back_btn.click()
        except:
            pass

        WebDriverWait(self._driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='tel']")
            )
        )

        tel_field = self._driver.find_element(
            By.CSS_SELECTOR, "input[type='tel']"
        )

        tel_field.send_keys(Keys.CONTROL + "a")
        tel_field.send_keys(Keys.DELETE)

    def _try_exit_profile(self, override_timeout: int = 20):
        if self._account_not_logined:
            return

        try:
            WebDriverWait(self._driver, override_timeout).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-test-id='profile-toggle']")
                )
            )
        except:
            self._account_not_logined = True

            print("ACCOUNT NOT LOGINED")
            return

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-test-id='profile-toggle']"
        ).click()

        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button[data-test-id='profile-popup-exit']")
                )
            )
        except:
            self._account_not_logined = False
            print("POPUP DONT OPEN")
            return
            # raise Exception("Popup dont opened")

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-test-id='profile-popup-exit']"
        ).click()

        WebDriverWait(self._driver, 60).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "input[id='pan']")
            )
        )

    def _click_submit_payment_form(self, override_timeout: int = 10):
        WebDriverWait(self._driver, override_timeout).until(
            expected_conditions.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-test-id='submit-payment']")
            )
        )

        self._card_data_page_path = self._driver.current_url

        self._driver.find_element(
            By.CSS_SELECTOR,
            "button[data-test-id='submit-payment']"
        ).click()

    def _click_subscription_button(self, override_timeout: int = 3):
        WebDriverWait(self._driver, override_timeout).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "button[class='css-kbwmb3']")
            )
        )

        self._driver.find_element(
            By.CSS_SELECTOR, "button[class='css-kbwmb3']"
        ).click()
