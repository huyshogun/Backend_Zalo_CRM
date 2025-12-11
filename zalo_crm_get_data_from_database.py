import zalo_crm_global_variables as gvars
from zalo_crm_crud_database import get_base_id_zalo_json
from zalo_crm_other_functions import load_data_chat_box_json

@gvars.app.route('/api_get_list_users', methods=['POST', 'GET'])
def get_list_users_new():
    data_body = gvars.request.form
    user_id = data_body.get('user_id')
    if user_id == "22495550":
        device_and_port = []
        for id in list(gvars.id_port.keys()):

            device_and_port += gvars.id_port[id]
    else:
        device_and_port = gvars.id_port[user_id]

    user_db = []
    status = True
    seen = []
    for dp in device_and_port:
        ports = list(dp.keys())
        port = ports[0]
        if port in seen:
            continue
        seen.append(port)
        device_id = dp[port]
        try:
            with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{device_id}.json', 'r', encoding='utf-8') as f:
                zalo_data = gvars.json.load(f)
            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{device_id}.json', 'r') as f:
                device_status = gvars.json.load(f)
            if 'update' in device_status.keys():
                if not device_status['update']:
                    continue
                    # status = device_status['update']
            for zalo in zalo_data:
                if zalo['name'] == "" or zalo['name'] == "Thêm tài khoản" or zalo['num_phone_zalo'] == "" or zalo['num_phone_zalo'] not in gvars.dict_device_and_phone[device_id]:
                    continue

                if device_id in list(gvars.device_connect.keys()):
                    if gvars.device_connect[device_id]:
                        connect = True
                    else:
                        connect = False
                else:
                    connect = False

                ava = ""
                if zalo['ava'] != "":
                    if zalo['ava'][0] == 'C':
                        with open(zalo['ava'], "r", encoding="utf-8") as f:
                            ava = f.read()
                    else:
                        ava = zalo['ava']

                user_db.append({"num_phone_zalo": zalo['num_phone_zalo'], "connect": connect, "name_device": port,
                               "status": zalo['status'], "user_name": zalo['name'], "avatar": ava, "port": port})
        except Exception as e:
            print(e)
            pass
    if len(user_db) == 0:
        status = False

    return gvars.jsonify({'user_db': user_db, 'update': status})


@gvars.app.route('/api_get_list_friend', methods=['POST', 'GET'])
def get_list_friend_new():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_friend")

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_friend']
    for id in range(len(result)):
        if result[id]['ava'] != "":
            if result[id]['ava'][0] == 'C':
                with open(result[id]['ava'], "r", encoding="utf-8") as f:
                    result[id]['ava'] = f.read()
    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_friend": result}), 200


@gvars.app.route('/api_get_list_group', methods=['POST', 'GET'])
def get_list_group_new():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    gvars.list_socket_call.append("get_list_group")
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    # now_phone_zalo[id_device] = num_phone_zalo
    result = document['list_group']
    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_group": result}), 200


@gvars.app.route('/api_get_list_invite_friend', methods=['POST', 'GET'])
def get_list_invite_friend_new():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    gvars.list_socket_call.append("get_list_group")
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    # now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_invite_friend']
    for id in range(len(result)):
        if result[id]['ava'] != "":
            if result[id]['ava'][0] == 'C':
                with open(result[id]['ava'], "r", encoding="utf-8") as f:
                    result[id]['ava'] = f.read()
    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_invite_friend": result}), 200


@gvars.app.route('/api_get_list_prior_chat_boxes', methods=['POST', 'GET'])
def get_list_prior_chat_boxes_new():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_prior_chat_boxes")
    # print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})

    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)

    # docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    list_friend = document['list_friend']
    friend = [fr['name'] for fr in list_friend]
    result = document['list_prior_chat_boxes']
    for id in range(len(list_friend)):
        if list_friend[id]['ava'] != "":
            if list_friend[id]['ava'][0] == 'C':
                with open(list_friend[id]['ava'], "r", encoding="utf-8") as f:
                    list_friend[id]['ava'] = f.read()
    for id in range(len(result)):
        # result[id]['ava'] = ""
        for it in range(len(friend)):
            if result[id]['name'] == friend[it]:
                result[id]['ava'] = list_friend[it]['ava']
                break
    for i1 in range(len(result)):
        if 'data_chat_box' in result[i1].keys():
            result[i1]['data_chat_box'] = load_data_chat_box_json(result[i1]['data_chat_box'])

            for i2 in range(len(result[i1]['data_chat_box'])):
                for k in result[i1]['data_chat_box'][i2].keys():
                    for i3 in range(len(result[i1]['data_chat_box'][i2][k])):
                        if "sticker_data" in result[i1]['data_chat_box'][i2][k][i3].keys():
                            ava64 = result[i1]['data_chat_box'][i2][k][i3]['sticker_data']
                            if ava64 != "":
                                if ava64[0] == 'C':
                                    with open(ava64, "r", encoding="utf-8") as f:
                                        result[i1]['data_chat_box'][i2][k][i3]['sticker_data'] = f.read(
                                        )
                        if "video_data" in result[i1]['data_chat_box'][i2][k][i3].keys():
                            ava64 = result[i1]['data_chat_box'][i2][k][i3]['video_data']
                            if ava64 != "":
                                if ava64[0] == 'C':
                                    with open(ava64, "r", encoding="utf-8") as f:
                                        result[i1]['data_chat_box'][i2][k][i3]['video_data'] = f.read(
                                        )
                        if "image_data" in result[i1]['data_chat_box'][i2][k][i3].keys():
                            ava64 = result[i1]['data_chat_box'][i2][k][i3]['image_data']
                            if ava64 != "":
                                if ava64[0] == 'C':
                                    with open(ava64, "r", encoding="utf-8") as f:
                                        result[i1]['data_chat_box'][i2][k][i3]['image_data'] = f.read(
                                        )

    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_prior_chat_boxes": result}), 200


@gvars.app.route('/api_get_list_unseen_chat_boxes', methods=['POST', 'GET'])
def get_list_unseen_chat_boxes_new():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_unseen_chat_boxes")
    # print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]

# docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_unseen_chat_boxes']
    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_unseen_chat_boxes": result}), 200


@gvars.app.route('/api_get_data_one_chat_box', methods=['POST', 'GET'])
def get_data_one_chat_box():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    # global now_phone_zalo
    # now_phone_zalo = new_id
    name_ntd = data_body.get('name_ntd')
    # num_send_phone_zalo = data_body.get('num_send_phone_zalo')
    num_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_prior_chat_boxes")
    result = []
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        gvars.now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    for id in list_prior_chat_boxes:
        if id['name'] == name_ntd:
            if 'data_chat_box' not in id.keys():
                id['data_chat_box'] = ""
            result = load_data_chat_box_json(id['data_chat_box'])
            break
        if "phone" in id.keys():
            if id['phone'] == name_ntd:
                name_ntd = id['name']
                if 'data_chat_box' not in id.keys():
                    id['data_chat_box'] = ""
                result = load_data_chat_box_json(id['data_chat_box'])
                break

    return gvars.jsonify({"num_phone_zalo": num_phone_zalo, "user_name": name_ntd, "data_chat_box": result}), 200


@gvars.socketio.on('socket_get_data_one_chat_box')
def get_data_one_chat_box(data):
    new_id = data['num_phone_zalo']
    name_ntd = data['name_ntd']
    room = data['id_chat']
    # global now_phone_zalo
    # now_phone_zalo = new_id
    # num_send_phone_zalo = data_body.get('num_send_phone_zalo')
    num_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_prior_chat_boxes")
    result = []
    friend_or_not = "yes"
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        gvars.now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    for id in list_prior_chat_boxes:
        if id['name'] == name_ntd:
            if 'data_chat_box' not in id.keys():
                result = []
            else:
                result = load_data_chat_box_json(id['data_chat_box'])

                for i2 in range(len(result)):
                    for k in result[i2].keys():
                        for i3 in range(len(result[i2][k])):
                            if "sticker_data" in result[i2][k][i3].keys():
                                ava64 = result[i2][k][i3]['sticker_data']
                                if ava64 != "":
                                    if ava64[0] == 'C':
                                        with open(ava64, "r", encoding="utf-8") as f:
                                            result[i2][k][i3]['sticker_data'] = f.read(
                                            )
                            if "video_data" in result[i2][k][i3].keys():
                                ava64 = result[i2][k][i3]['video_data']
                                if ava64 != "":
                                    if ava64[0] == 'C':
                                        with open(ava64, "r", encoding="utf-8") as f:
                                            result[i2][k][i3]['video_data'] = f.read()
                            if "image_data" in result[i2][k][i3].keys():
                                ava64 = result[i2][k][i3]['image_data']
                                if ava64 != "":
                                    if ava64[0] == 'C':
                                        with open(ava64, "r", encoding="utf-8") as f:
                                            result[i2][k][i3]['image_data'] = f.read()
            if 'friend_or_not' not in id.keys():
                friend_or_not = "yes"
            else:
                friend_or_not = id['friend_or_not']
            break
    gvars.join_room(room)
    gvars.emit("receive_data_one_chat_box", {
        "num_phone_zalo": num_phone_zalo, "user_name": name_ntd, "data_chat_box": result, "friend_or_not": friend_or_not}, room=room)
