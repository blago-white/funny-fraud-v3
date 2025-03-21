from aiohttp import web


async def receive_sms(request: web.Request):
    data = await request.post()

    print(f"RECEIVE SMS FROM MOBILE: {data} ")

    return web.Response(text=b"Received!")


app = web.Application()
app.add_routes(routes=[
    web.get("/receive-sms/", receive_sms)
])
web.run_app(app=app, port=80)
