import aiohttp
import asyncio
import io
import datetime, time
import json
from pi_client_json_maker import *
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

ip_addr = "home.slawn64.cf"
remote_port = "8086"
mp_url_path = "/json"
full_url = "http://" + ip_addr + ":" + remote_port + mp_url_path

LOCAL_DEVICE_ID = None  # 本機的 ID，用八位數字表示
HTTP_FAILED_COUNT = 0


async def request_http(data, timeout_settings):
    async with aiohttp.ClientSession() as session:  # open a session

        header = {'content-type': 'text/json'}
        async with session.post(full_url, data=data, headers=header, timeout=timeout_settings) as resp:
            # print("收取結果中，，，")
            code = resp.status
            result = await resp.text()
            return code, result


async def http_client_task():
    # TODO global POWER_ON, AUTO_BRIGHTNESS, BRIGHTNESS
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
                timeout_setting = aiohttp.ClientTimeout(total=3*60)
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
                    command = mdict["query"]["type"]
                    logging.info("The command is " + command)
                    if command == "error":
                        raise ValueError("test error")
                except Exception as error:
                    # 命令有問題
                    logging.error("The command has some problem")
                    sender = mdict["from"]
                    error_json = make_json("error", origin=LOCAL_DEVICE_ID,
                                           destination=sender, query_type="Command error")
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



loop = asyncio.get_event_loop()

if __name__ == '__main__':

    loop.create_task(http_client_task())
    loop.run_forever()
