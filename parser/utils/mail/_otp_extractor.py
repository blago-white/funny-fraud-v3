def extract_otp_from_mail(mail_text: str) -> str:
    return mail_text.split("</p>")[-2][-5:]
