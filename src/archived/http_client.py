import aiohttp
import asyncio

ip_addr = "127.0.0.1"
remote_port = "8086"
mp_url_path = "/mp"
full_url = "http://" + ip_addr + ":" + remote_port + mp_url_path


async def request_http(data):
    async with aiohttp.ClientSession() as session:
        with aiohttp.MultipartWriter() as mpwriter:
            part = mpwriter.append(data)
            # part.set_content_disposition('binary')
            part.headers[aiohttp.hdrs.CONTENT_TYPE] = 'binary'
            mpwriter.append("the local size is " + str(len(data)))
            async with session.post(full_url, data=mpwriter) as resp:
                print('HTTP code is ', resp.status)
                print(await resp.text())


def read_file():  # 輸入檔案路徑，將檔案存入記憶體，返回位元組數組
    filename = input('copy your file uri here: ')
    filename = filename.replace('\"','',2)
    try:
        file_handle = open(filename, 'br')
    except Exception as esu:  # 嘗試二進位打開檔案
        print(esu)
        return None
    finally:
        data_read = bytearray(file_handle.read())
        file_handle.close()
        return data_read


if __name__ == '__main__':
    data = read_file()
    # print(len(data))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(request_http(data))
