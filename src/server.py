import asyncio
import time
import threading
from math import sqrt
from datetime import datetime


def repeat(message):
    time.sleep(3)
    print(message)


if __name__ == "__main__":
   # worker = asyncio.get_event_loop()
    while True:
        user_input = input("please input something\n")
        threading.Thread(target=repeat, args=[user_input]).start()
        print('ok!')
