import json, time


def make_json(action, origin=None, destination=None, query_type=None, query_list=None):
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
    else:
        template["query"].update({"type": ""})

    return json.dumps(template)
