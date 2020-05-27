import aiohttp
import asyncio
import io
import datetime, time
import json
import smbus
import time
import sys
import os
import RPi.GPIO as GPIO
import serial
import logging
from pi_client_json_maker import make_json

# 日誌記錄級別
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

# 服務端地址
ip_addr = "home.slawn64.cf"
remote_port = "8086"
mp_url_path = "/json"
full_url = "http://" + ip_addr + ":" + remote_port + mp_url_path

# 設定 GPIO
GPIO.setwarnings(False)
DEVICE = 0x23

ONE_TIME_HIGH_RES_MODE_1 = 0x20
ONE_TIME_HIGH_RES_MODE_2 = 0x21

GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)
GPIO.setup(40, GPIO.IN, pull_up_down=GPIO.PUD_UP)

ser = serial.Serial("/dev/rfcomm0", 9600, timeout=0.5)
ser.write("test ".encode())

bus = smbus.SMBus(1)

# 控制用變數
POWER_ON = False
AUTO_BRIGHTNESS = False
BRIGHTNESS = 4
LED_GPIO_INDEX = [11, 16, 13, 15]
TOUCH_SWITCH_GPIO = 40
TOUCH_LONG_THRESHOLD_MILISEC = 1500  # 觸控板長按時間閾值
LIGHT_DETECT_INTERVAL_SEC = 5  # 亮度探測間隔
LOCAL_DEVICE_ID = None  # 本機的 ID，用八位數字表示
HTTP_FAILED_COUNT = 0

# 支援的遠端命令
SUPPORTED_COMMAND = [
    "POWER_ON",
    "POWER_OFF",
    "AUTO_BRIGHTNESS_ON",
    "AUTO_BRIGHTNESS_OFF",
    "BRIGHTNESS_SET"
]


def convertToNumber(data):
    return (data[1] + (256 * data[0])) / 1.2


def readLight(addr=DEVICE):
    data = bus.read_i2c_block_data(addr, ONE_TIME_HIGH_RES_MODE_2)
    return convertToNumber(data)


# 更改亮度
def output_brightness(brightness):
    for i in range(brightness):
        GPIO.output(LED_GPIO_INDEX[i], GPIO.HIGH)
    for i in range(brightness, len(LED_GPIO_INDEX)):
        GPIO.output(LED_GPIO_INDEX[i], GPIO.LOW)


# 循環監聽狀態
async def led_control_task():
    global POWER_ON, BRIGHTNESS, LED_GPIO_INDEX
    while True:
        if POWER_ON:
            output_brightness(BRIGHTNESS)
        else:
            output_brightness(0)

        await asyncio.sleep(0.05)


# 觸摸板操作
async def touch_switch_task():
    global POWER_ON, AUTO_BRIGHTNESS, BRIGHTNESS
    time_pressed = 0
    while True:
        if GPIO.input(TOUCH_SWITCH_GPIO) and time_pressed == 0:
            time_pressed = int(time.time() * 1000)
        if not GPIO.input(TOUCH_SWITCH_GPIO) and time_pressed != 0:
            time_elapsed = int(time.time() * 1000) - time_pressed
            time_pressed = 0
            if time_elapsed < TOUCH_LONG_THRESHOLD_MILISEC:
                # 短按操作：開關電源
                logging.info("Touch bar short pressed")
                if POWER_ON:
                    POWER_ON = False
                    BRIGHTNESS = 4
                    logging.info("Power off")
                else:
                    POWER_ON = True
                    logging.info("Power on")
            else:
                logging.info("Touch bar long pressed")
                # 長按操作：開關自動亮度
                if POWER_ON:
                    if AUTO_BRIGHTNESS:
                        AUTO_BRIGHTNESS = False
                        BRIGHTNESS = 4
                        logging.info("Auto brightness off")
                    else:
                        AUTO_BRIGHTNESS = True
                        logging.info("Auto brightness on")

                else:
                    logging.info("The Power is off, turn on the power first")

        await asyncio.sleep(0.03)


# 亮度感應器操作
async def light_detector_task():
    global AUTO_BRIGHTNESS, BRIGHTNESS
    while True:
        if AUTO_BRIGHTNESS:
            num = readLight()
            if num < 100:
                BRIGHTNESS = 1
            elif 100 <= num < 400:
                BRIGHTNESS = 2
            elif 400 <= num < 800:
                BRIGHTNESS = 3
            elif 800 <= num:
                BRIGHTNESS = 4
            logging.debug("Detected: " + str(num) + " Set: " + str(BRIGHTNESS))

        await asyncio.sleep(LIGHT_DETECT_INTERVAL_SEC)


# 蓝牙通信操作
async def bluetooth_task():
    global BRIGHTNESS
    while True:
        if POWER_ON:
            count = ser.inWaiting()
            if count != 0:
                recv = ser.read(count)
                # TODO: 字符串怎麼讀出來？
                logging.info("Bluetooth recv: " + str(recv))
                if recv == b'31':
                    BRIGHTNESS = 4
                else:
                    BRIGHTNESS = 0
        else:
            pass

        await asyncio.sleep(0.05)


# HTTP 客戶端
async def http_client_task():
    global POWER_ON, AUTO_BRIGHTNESS, BRIGHTNESS
    global LOCAL_DEVICE_ID, HTTP_FAILED_COUNT
    while True:
        try:
            if LOCAL_DEVICE_ID is None:
                logging.info("Need register")
                # start register here
                # require server response in 5 sec otherwise error
                timeout_setting = aiohttp.ClientTimeout(total=5)
                register_json = make_json(action="register", query_type="controlled")
                code, result = await request_http(register_json, timeout_setting)
                if verify_http_code_result(code, result, "id_delegation"):
                    mdict = json.loads(result)
                    # 註冊成功
                    LOCAL_DEVICE_ID = mdict["query"]["1"]
                    logging.info("Register success, id = " + LOCAL_DEVICE_ID)
                    HTTP_FAILED_COUNT = 0

            # 現在有了 ID，可以開始 long polling 了
            try:
                polling_json = make_json(action="request", origin=LOCAL_DEVICE_ID)
                timeout_setting = aiohttp.ClientTimeout(total=3 * 60)
                # 超時設定爲三分鐘
                logging.info("Long polling start")
                code, result = await request_http(polling_json, timeout_setting)
                logging.info("New command polled")

            except asyncio.TimeoutError as err:
                # 超過時間伺服器沒回應，重新 poll
                logging.info("Server did not response anything, poll again")
                continue

            if verify_http_code_result(code, result, "command"):
                # 現在進行命令的執行等
                mdict = json.loads(result)

                try:
                    command_executor(mdict["query"])

                except (json.JSONDecodeError, ValueError) as error:
                    # 命令有問題，回傳一條錯誤
                    logging.error("The command has some problem")
                    sender = mdict["from"]
                    error_json = make_json("error", origin=LOCAL_DEVICE_ID,
                                           destination=sender, query_type=str(error))
                    timeout_setting = aiohttp.ClientTimeout(total=5)
                    code, result = await request_http(error_json, timeout_setting)
                    verify_http_code_result(code, result, "send")

        except ConnectionRefusedError as error:
            # 需要重新註冊
            logging.error("本機未註冊：" + str(error))
            LOCAL_DEVICE_ID = None

        except Exception as error:
            # 出現的未經內層 catch 的 exception 會導致重試次數增加
            HTTP_FAILED_COUNT = HTTP_FAILED_COUNT + 1
            logging.error("Error occurred in http client: " + str(error))
            logging.error("The failed count is: " + str(HTTP_FAILED_COUNT))

        finally:
            # 重試得越多，重試間隔就越大
            logging.info("HTTP will restart in " + str(HTTP_FAILED_COUNT * 5) + " seconds")
            await asyncio.sleep(HTTP_FAILED_COUNT * 5 + 0.05)


# HTTP 請求模組
async def request_http(data, timeout_settings):
    async with aiohttp.ClientSession() as session:  # open a session

        header = {'content-type': 'text/json'}
        async with session.post(full_url, data=data, headers=header, timeout=timeout_settings) as resp:
            # print("收取結果中，，，")
            code = resp.status
            result = await resp.text()
            return code, result


# JSON 校驗模組
def verify_http_code_result(code, result_json, expected_action):
    supported_action = ["id_delegation", "peer_found", "command", "send"]
    if expected_action not in supported_action:
        return False

    has_error = False
    error_msg = ""
    if not 200 <= code <= 299:
        has_error = True
        error_msg = error_msg + "Error HTTP code is: " + str(code) + "\n"
        if code == 401:  # 未註冊
            raise ConnectionRefusedError(error_msg)

    try:
        json_dict = json.loads(result_json)
        if json_dict["action"] == "error":
            has_error = True
            error_msg = error_msg + "Server reported an error: " \
                        + json_dict["query"]["type"] + "\n"
            raise ValueError(error_msg)
    except Exception as error:
        has_error = True
        error_msg = error_msg + "The json has an error: " + str(error) + "\n"
        raise ValueError(error_msg)

    if expected_action == "id_delegation":
        if json_dict["action"] != "response" or json_dict["query"]["type"] != "id_delegation":
            has_error = True
            error_msg = error_msg + "id_delegation has a problem.\n"
            raise ValueError(error_msg)

    if expected_action == "peer_found":
        if json_dict["action"] != "response" or json_dict["query"]["type"] != "peer_found":
            has_error = True
            error_msg = error_msg + "peer_found has a problem.\n"
            raise ValueError(error_msg)

    if expected_action == "command":
        if json_dict["action"] != "command" or "type" not in json_dict["query"]:
            has_error = True
            error_msg = error_msg + "This Command has a problem.\n"

    if has_error:
        return False
    else:
        return True


# 從 query 的 dict 執行命令
def command_executor(command_query):
    global POWER_ON, BRIGHTNESS, AUTO_BRIGHTNESS
    if command_query["type"] not in SUPPORTED_COMMAND:
        raise ValueError("Unsupported command")

    command_type = command_query["type"]
    query_list = []
    for onekey in command_query.keys():
        if onekey == "type":
            continue
        query_list.append(command_query[onekey])

    if command_type == "POWER_ON":
        POWER_ON = True

    if command_type == "POWER_OFF":
        POWER_ON = False

    if command_type == "AUTO_BRIGHTNESS_ON":
        AUTO_BRIGHTNESS = True

    if command_type == "AUTO_BRIGHTNESS_OFF":
        AUTO_BRIGHTNESS = False

    if command_type == "BRIGHTNESS_SET":
        try:
            if int(query_list[0]) in range(1, 5):
                AUTO_BRIGHTNESS = False
                BRIGHTNESS = int(query_list[0])
            else:
                raise ValueError("Brightness Value not allowed")
        except Exception as err:
            raise ValueError(err)


def main():
    loop.create_task(led_control_task())
    loop.create_task(touch_switch_task())
    loop.create_task(light_detector_task())
    loop.create_task(http_client_task())
    loop.create_task(bluetooth_task())

    loop.run_forever()


loop = asyncio.get_event_loop()

if __name__ == '__main__':
    main()
