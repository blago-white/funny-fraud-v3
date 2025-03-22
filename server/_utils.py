def _extract_otp_code(content: str) -> str:
    return "".join(list(filter(
        lambda c: c.isdigit(),
        content.split("message")[-1]
    ))[:4])
