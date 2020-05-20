import asyncio
import json

import aiohttp
from aiohttp import web
from action_handler import for_request, for_command, for_register, make_response_json


async def the_mp_server(request):
    reader = await request.multipart()
    json_str = None
    while True:
        part = await reader.next()
        if part is None:
            break
        # print(part.headers)
        if part.headers[aiohttp.hdrs.CONTENT_TYPE] == 'json':
            # print('json found!')
            # await asyncio.sleep(3)
            json_str = await part.read()
            print(json_str)

    return await json_str_parser(json_str)


async def the_json_server(request):
    json_str = await request.text()
    print("new connection " + json_str)
    return await json_str_parser(json_str)


async def json_str_parser(json_str):
    if json_str is not None:
        try:
            the_json = json.loads(json_str)
            verify_json_dict(the_json)
            the_action = the_json["action"]
            # print(the_json)
            if the_action == "request":
                mResponse = await for_request(the_json)
            elif the_action == "command":
                mResponse = await for_command(the_json)
            elif the_action == "register":
                mResponse = await for_register(the_json)
            # elif the_action == "response":
                pass
            else:
                raise ValueError("field action" + the_action + "not allowed")

        except Exception as err:
            return web.Response(status=400, text=make_response_json("error", origin="server",
                                                                    query_type="json error " + str(err)))

    else:
        return web.Response(status=400, text=make_response_json("error",  origin="server",
                                                                query_type="json error or invalid"))

    return mResponse


async def web_page(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


def verify_json_dict(the_dict):
    keys = the_dict.keys()
    should_have_keys = ["time", "from", "to", "action", "query"]
    for thekey in should_have_keys:
        if thekey not in keys:
            raise ValueError("Field " + thekey + " not exist!")
    if the_dict["action"] == "command":
        to_dest = the_dict["to"]
        if to_dest is None or len(to_dest) == 0:
            raise ValueError("destination of command error")


app = web.Application()
app.add_routes([web.post('/mp', the_mp_server),
                web.post('/json', the_json_server),
                web.get('/{name}', web_page)])
loop = asyncio.get_event_loop()


def main():
    # make configuration of aiohttp
    runner = aiohttp.web.AppRunner(app=app)
    loop.run_until_complete(runner.setup())
    site = aiohttp.web.TCPSite(runner=runner, port=8086)
    loop.run_until_complete(site.start())

    loop.run_forever()


if __name__ == '__main__':
    main()
    # web.run_app(app, port=8086)
