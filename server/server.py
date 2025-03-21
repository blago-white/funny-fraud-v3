import multiprocessing
import threading

from aiohttp import web

from .services.sms import ClientSmsCodesService


def _extract_code(content: str):
    return "".join(list(filter(
        lambda content: content.isdigit(),
        content.split("message\": \"")[-1]
    ))[:4])


async def receive_sms(request: web.Request):
    content = (await request.content.read()).decode("UTF-8")

    client_sms_service = ClientSmsCodesService()

    print(f"RECEIVE SMS FROM CLIENT: {content}")

    if "Покупка 1р" in content:
        print("CLIENT SIDE PAYMENT COMPLETE!")
        client_sms_service.payment_completed()

    if "Списание 1р" in content:
        otp_code = _extract_code(content=content)

        print(f"CLIENT SIDE OTP RECEIVED: {otp_code}")

        client_sms_service.register_code(code=otp_code)

    return web.Response(status=201)


def _run_app():
    print("START SERVING")

    app = web.Application()
    app.add_routes(routes=[
        web.post("/receive-sms/", receive_sms)
    ])
    web.run_app(app=app, port=8080)


def start_server_pooling():
    th = multiprocessing.Process(target=_run_app)
    th.start()
    print("=== SMS SERVER PROCESS STARTED ===")
