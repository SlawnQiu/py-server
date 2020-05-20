import asyncio

import aiohttp
from aiohttp import web


async def calc_size(request):
    reader = await request.multipart()
    binary = None
    while True:
        part = await reader.next()
        if part is None:
            break
        print(part.headers)
        if part.headers[aiohttp.hdrs.CONTENT_TYPE] == 'binary':
            print('file found!')
            await asyncio.sleep(3)
            binary = await part.read()
    if binary is not None:
        print(len(binary))

    return web.Response(text='接收資料成功，資料大小 '+str(len(binary)))


async def web_page(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


app = web.Application()
app.add_routes([web.post('/mp', calc_size),
                web.get('/{name}', web_page)])

if __name__ == '__main__':
    web.run_app(app, port=8086)
