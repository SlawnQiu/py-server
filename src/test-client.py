import aiohttp
import asyncio
import io
import datetime, time
import json

ip_addr = "home.slawn64.cf"
remote_port = "8086"
mp_url_path = "/json"
full_url = "http://" + ip_addr + ":" + remote_port + mp_url_path


async def request_http(data):
    async with aiohttp.ClientSession() as session:  # open a session
        #with aiohttp.MultipartWriter() as mpwriter:  # make a multipart writer
            # print("包裝 multipart 中：二進位")
            # part = mpwriter.append(data)  # add a part include the photo data
            # part.set_content_disposition('binary')
            # part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'binary'
            #print("包裝 multipart 中：字串")
            #part = mpwriter.append(data)
            #part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'json'
            # use the default content type plain/text
            #print("送出 multipart 中，，，")
            #async with session.post(full_url, data=mpwriter) as resp:
        header = {'content-type': 'text/json'}
        async with session.post(full_url, data=data, headers=header) as resp:
            print("收取結果中，，，")
            code = resp.status
            result = await resp.text()
            return code, result


def make_query():  # return String
    query = {"type": ""}
    obj = {}
    obj.update({"time": str(int(time.time()*1000)),
                "from": "W9O0D3qR", # 這裏填上本機 ID
                "to": "",  # input("input the target"),
                "action": input("input the action "),
                "query": query})
    return json.dumps(obj)  # dumps 將 字典 dict 轉換爲 json 字串 string


if __name__ == '__main__':
    query = make_query()
    code, result = asyncio.run(request_http(query))
    print(code, result)

