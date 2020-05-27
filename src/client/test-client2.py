import aiohttp
import asyncio
import io
import datetime, time
import json

ip_addr = "127.0.0.1"
remote_port = "8086"
mp_url_path = "/mp"
full_url = "http://" + ip_addr + ":" + remote_port + mp_url_path


async def request_http(data):
    async with aiohttp.ClientSession() as session:  # open a session
        with aiohttp.MultipartWriter() as mpwriter:  # make a multipart writer
            # print("包裝 multipart 中：二進位")
            # part = mpwriter.append(data)  # add a part include the photo data
            # part.set_content_disposition('binary')
            # part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'binary'
            print("包裝 multipart 中：字串")
            part = mpwriter.append(data)
            part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'json'
            # use the default content type plain/text
            print("送出 multipart 中，，，")
            async with session.post(full_url, data=mpwriter) as resp:
                print("收取結果中，，，")
                code = resp.status
                result = await resp.text()
                print(code, result)


def make_query():  # return String
    query = {"3": "cmd1", "4": "cmd2"}
    obj = {}
    obj.update({"time": str(time.time()),
                "from": "0002",
                "to": "0001",  # input("input the target"),
                "action": "command",
                "query": query})
    return json.dumps(obj)


loop = asyncio.get_event_loop()


if __name__ == '__main__':
    query = make_query()
    # code, result = asyncio.run(request_http(query))
    # loop.create_task(request_http(query))
    loop.run_until_complete(request_http(query))

    # print(code, result)
    # 0001 被控
    # 0002 遙控
