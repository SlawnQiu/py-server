import asyncio, time, string, random, logging
import json
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

queue_dict = {}  # usage: "ID": the Queue
registerd_dict = {}  # usage "ID": {"type": "controller or controlled", "time": time}


async def for_request(query_dict):
    try:
        pass
        if_id_registered([query_dict["from"]])
    except ValueError as err:
        return web.Response(status=401, text=make_response_json("error", origin="server", query_type="You are "
                                                                                                     "Unauthorized"))
    try:
        if query_dict["query"]["type"] == "peer_finding":
            return response_registered_peer()
    except:
        pass

    if query_dict["from"] not in queue_dict:
        q = asyncio.Queue()
        queue_dict.update({query_dict["from"]: q})
        logging.debug("no queue called " + query_dict["from"])
    else:
        q = queue_dict[query_dict["from"]]
        logging.debug("there is a queue called " + query_dict["from"])

    while True:
        if q.empty():
            await asyncio.sleep(0.01)
        else:
            break
    logging.debug("there are something in the queue ")

    message = q.get_nowait()

    # print(message)
    return web.Response(status=200, text=json.dumps(message))


async def for_command(query_dict):
    try:
        if_id_registered([query_dict["from"]])
    except ValueError as err:
        return web.Response(status=401, text=make_response_json("error", query_type="You are Unauthorized"))

    try:
        if_id_registered([query_dict["to"]])
    except ValueError as err:
        return web.Response(status=404, text=make_response_json("error", query_type="Destination is " + str(err)))

    if query_dict["to"] not in queue_dict:
        q = asyncio.Queue()
        queue_dict.update({query_dict["to"]: q})
        logging.debug("no queue called " + query_dict["to"])
    else:
        q = queue_dict[query_dict["to"]]
        logging.debug("there is a queue called " + query_dict["to"])

    await q.put(query_dict)
    resptext = make_response_json("response", query_type="command_created", origin="server")
    return web.Response(status=201, text=resptext)


async def for_register(query_dict):
    try:
        the_type = query_dict["query"]["type"]
        type_dict = {
            "controller": "controller",
            "controlled": "controlled"
        }
        the_type = type_dict[the_type]
    except Exception as err:
        resptext = make_response_json("error", query_type="register error" + str(err))
        return web.Response(status=400, text=resptext)
    # request legal

    chars = string.digits
    the_id = ''.join([random.choice(chars) for _ in range(8)])

    registerd_dict.update({the_id: {"type": the_type, "time": str(int(time.time()))}})

    logging.info("The device " + the_id + " registered as " + the_type)
    resptext = make_response_json("response", query_type="id_delegation", origin="server", query_list=[the_id])
    return web.Response(status=200, text=resptext)


def if_id_registered(ids):
    for the_id in ids:
        if the_id not in registerd_dict:
            raise ValueError("no registered id of " + str(the_id))
        else:
            registerd_dict[the_id]["time"] = str(int(time.time()))


def make_response_json(action, origin=None, destination=None, query_type=None, query_list=None):
    template = {
        "time": str(int(time.time() * 1000)),

    }
    if origin is not None:
        template.update({"from": origin})
    else:
        template.update({"from": ""})
    if destination is not None:
        template.update({"to": destination})
    else:
        template.update({"to": ""})
    template.update({"action": action})
    template.update({"query": {}})
    if query_type is not None:
        template["query"].update({"type": query_type})
        i = 0
        if query_list is not None:
            for item in query_list:
                i = i + 1
                template["query"].update({str(i): item})

    return json.dumps(template)


def response_registered_peer():
    device_list = []
    for deviceid in registerd_dict:
        if registerd_dict[deviceid]["type"] == "controlled" or registerd_dict[deviceid]["type"] == "controller":
            if int(time.time()) - int(registerd_dict[deviceid]["time"]) > 200:
                continue  # 如果 200 秒不活躍，不再包括在返回的 peer 列表裏
            device_list.append(registerd_dict[deviceid]["type"])
            device_list.append(deviceid)
    resptext = make_response_json("response", query_type="peer_found", query_list=device_list)
    return web.Response(status=200, text=resptext)
