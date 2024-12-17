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

    def submit_payment(self):
        self._submit_payment_form()

    def enter_registration_code(self, code: str):
        self._enter_registration_code(code=code)

        self._check_registration_code_correct()

        self._enter_owner_data()

    def enter_payment_card_otp(self, code: str, _retry: bool = 3):
        if _retry == 3:
            WebDriverWait(self._driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "passwordEdit")
                )
            )
        else:
            otp_field = self._driver.find_element(
                By.ID, "passwordEdit"
            )

            otp_field.send_keys(Keys.CONTROL+"a")
            otp_field.send_keys(Keys.DELETE)

        self._driver.find_element(
            By.ID, "passwordEdit"
        ).click()

        for i in code:
            self._driver.find_element(
                By.ID, "passwordEdit"
            ).send_keys(i)

        try:
            WebDriverWait(self._driver, 7).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[class='error']")
                )
            )
        except:
            try:
                WebDriverWait(self._driver, 60).until(
                    expected_conditions.presence_of_element_located(
                        (By.CSS_SELECTOR, "p[class='css-dth2xi']")
                    )
                )
                return True
            except:
                raise exceptions.OTPError("Success page not opened but "
                                          "code is ok")

        if not _retry:
            raise exceptions.InvalidOtpCodeError("Invalid otp code received")
        else:
            return self.enter_payment_card_otp(code=code, _retry=_retry-1)

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
        self._enter_card()

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

    def _enter_card(self):
        WebDriverWait(self._driver, 120).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "input[id='pan']")
            )
        )

        self._try_exit_profile()

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

    def _submit_payment_form(self):
        WebDriverWait(self._driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-test-id='submit-payment']")
            )
        )

        self._card_data_page_path = self._driver.current_url

        self._driver.find_element(
            By.CSS_SELECTOR,
            "button[data-test-id='submit-payment']"
        ).click()

        print("WAIT FOR OTP PASSWORD")

        START = time.time()

        while True:
            if time.time() - START > 20:
                print("PAYMENT URL DONT CHANGES")

                raise Exception("Cannot submit form")

            if self._driver.current_url != self._card_data_page_path:
                break

        print("PAYMENT URL CHANGES")

        try:
            WebDriverWait(self._driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "passwordEdit")
                )
            )
        except:
            WebDriverWait(self._driver, 10).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[class='css-kbwmb3']")
                )
            )

            self._driver.find_element(
                By.CSS_SELECTOR, "button[class='css-kbwmb3']"
            ).click()
            self._card_data_already_entered = False

            print("ERROR GETTING OTP CODE PAGE")

            raise exceptions.OTPError("Error getting otp page")

        print("OTP PASSWORD REQUEST COMPLETE")

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
                (By.CSS_SELECTOR, "button[data-testid='phoneNumber-nextButton']")
            )
        )

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='phoneNumber-nextButton']"
        ).click()

        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "inputError")
                )
            )
        except:
            pass
        else:
            raise Exception

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
            WebDriverWait(self._driver, 140).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".css-1tb3n43.e1jyzd9p2")
                )
            )
        except:
            raise exceptions.TraficBannedError("Change proxy, banned!")

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

    def _try_exit_profile(self):
        try:
            WebDriverWait(self._driver, 20).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-test-id='profile-toggle']")
                )
            )
        except:
            print("ACCOUNT NOT LOGINED")
            return

        self._driver.find_element(
            By.CSS_SELECTOR, "button[data-test-id='profile-toggle']"
        ).click()

        try:
            WebDriverWait(self._driver, 5).until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-test-id='profile-popup-exit']")
                )
            )
        except:
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
