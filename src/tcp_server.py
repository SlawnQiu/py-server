import asyncio


async def handle_echo(reader, writer):
    data_in: bytes = await reader.read(200)
    message = data_in.hex()
    addr = writer.get_extra_info('peername')
    print("Received %r from %r" % (message, addr))
    size = len(data_in)
    print("Send: %r" % size)
    writer.write(str(size).encode())
    await writer.drain()

    print("Close the client socket")
    writer.close()


if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_echo, '127.0.0.1', 8086, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
