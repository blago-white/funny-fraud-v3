class BaseEmailVerificationService:
    _email: str = None

    def get_mail(self) -> str:
        if self._email:
            return self._email

        raise NotImplementedError

    def get_code(self):
        raise NotImplementedError
