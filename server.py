from aiohttp import web


async def receive_sms(request: web.Request):
    data = await request.post()

    print(f"RECEIVE SMS FROM MOBILE: {data} {(await request.content.read())}")

    return web.Response(status=201)


app = web.Application()
app.add_routes(routes=[
    web.post("/receive-sms/", receive_sms)
])
web.run_app(app=app, port=80)

# import requests
#
# response = requests.post("http://185.197.75.89:80/receive-sms/", data={"h": "w"})
#
# print(response)
