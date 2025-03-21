import threading

from aiohttp import web


def _extract_code(content: str):
    return "".join(list(filter(
        lambda content: content.isdigit(),
        content.split("message\": \"")[-1]
    ))[:4])


async def receive_sms(request: web.Request):
    content = (await request.content.read()).decode("UTF-8")

    print(f"RECEIVE SMS FROM MOBILE: {content}")

    if "Покупка 1р" in content:
        print("ПОКУПКА ЕСТЬ")

    if "Списание 1р" in content:
        print("ОТП КОД")

        print(_extract_code(content=content))

    return web.Response(status=201)


def run_app():
    print("START SERVING")

    app = web.Application()
    app.add_routes(routes=[
        web.post("/receive-sms/", receive_sms)
    ])
    web.run_app(app=app, port=80)


th = threading.Thread(target=run_app)
th.start()
print("TH STARTED")

# import requests
#
# response = requests.post("http://185.197.75.89:80/receive-sms/", data={"h": "w"})
#
# print(response)
