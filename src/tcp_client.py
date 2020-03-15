import asyncio


async def tcp_client(data_in, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8086, loop=loop)

    print('Send: %r' % str(data_in.hex()))
    writer.write(data_in)
    await writer.drain()

    data_recv = await reader.read(100)
    print('Received: %r' % str(data_recv.hex()))

    print('Close the socket')
    writer.close()


#message = 'Hello World!'
#loop = asyncio.get_event_loop()

def read_file():  # 輸入檔案路徑，將檔案存入記憶體，返回位元組數組
    filename = input('copy your file uri here: ')
    try:
        file_handle = open(filename, 'br')
    except Exception as esu:  # 嘗試二進位打開檔案
        print(esu)
        return None
    finally:
        data_read = bytes(file_handle.read())
        file_handle.close()
        return data_read


if __name__ == '__main__':
    data = read_file()
    print(len(data),'\n')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tcp_client(data, loop))
    loop.close()