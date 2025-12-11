
import zalo_crm_global_variables as gvars
from zalo_crm_crud_database import get_base_id_zalo_json, update_base_document_json, already_sent_number, read_sent_number, log_sent_number, already_sent, log_sent
from zalo_crm_other_functions import switch_account

max_message_per_day = 300
num_message = 0
num_add_friend = 0
image_number = 300
max_add_friend_per_day = 30

@gvars.app.route('/api_click_tag', methods=['POST', 'GET'])
def get_click_tag():
    data_body = gvars.request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    tag = data_body.get('tag')
    name_ntd = data_body.get('name_ntd')
    gvars.list_socket_call.append("click_tag")

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        gvars.now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)

    list_prior_chat_boxes = document['list_prior_chat_boxes']
    check = False
    for id in range(len(list_prior_chat_boxes)):
        if list_prior_chat_boxes[id]['name'] == name_ntd:
            if 'tag' not in list_prior_chat_boxes[id].keys():
                list_prior_chat_boxes[id]['tag'] = ""
            if list_prior_chat_boxes[id]['tag'] == "":
                list_prior_chat_boxes[id]['tag'] = tag
                check = True
            else:
                if list_prior_chat_boxes[id]['tag'] != tag:
                    list_prior_chat_boxes[id]['tag'] = tag
                    check = True
                else:
                    list_prior_chat_boxes[id]['tag'] = ""
                    check = True
            if check:
                data_update = {"num_phone_zalo": num_phone_zalo,
                               "list_prior_chat_boxes": list_prior_chat_boxes}
                update_base_document_json(
                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
            break
    return gvars.jsonify({"status": "Đã click tag thành công"}), 200


@gvars.app.route('/find_new_friend', methods=['POST', 'GET'])
def api_find_new_friend():
    data = gvars.request.form
    room = data.get('id_chat', '')
    num_phone_zalo = data.get('num_phone_zalo')
    num_send_phone_zalo = data.get('num_send_phone_zalo')

    for k in gvars.dict_new_friend[num_phone_zalo].keys():
        if gvars.dict_new_friend[num_phone_zalo][k]['phone'] == num_send_phone_zalo:
            name_ntd = k
            avatar_64 = gvars.dict_new_friend[num_phone_zalo][k]['ava']
            friend_or_not = gvars.dict_new_friend[num_phone_zalo][k]['friend_or_not']
            return gvars.jsonify({"num_send_phone_zalo": num_send_phone_zalo, "name_ntd": name_ntd, "ava": avatar_64, "friend_or_not": friend_or_not}), 200

    one = gvars.time.time()
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        # print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    if gvars.dict_id_chat[id_device] != "" and gvars.dict_id_chat[id_device] != room:
        return gvars.jsonify({'status': "Thiết bị đang có người sử dụng"})
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    gvars.now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']

    # print("Đã vào được điện thoại này chưa")
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = gvars.dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if gvars.dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = gvars.dict_queue_device[id_device][0]
            gvars.eventlet.sleep(0.1)

        gvars.dict_status_update_pvp[num_phone_zalo] = 1
        gvars.dict_status_zalo[num_phone_zalo] = "find_new_friend"

        try:
            d = gvars.u2.connect(id_device)
            # global device_connect
            gvars.device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            gvars.device_connect[id_device] = False
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})

        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)
        try:
            ck_ac = True
            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    gvars.json.dump(device_status, f, indent=4)
                gvars.eventlet.sleep(0.1)
                ck_ac = False
                d.app_start("com.zing.zalo", stop=True)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    gvars.eventlet.sleep(0.05)

            name_ntd = ""
            pick = ""
            avatar_64 = ""
            friend_or_not = ""
            on_chat = False
            for id in range(len(list_prior_chat_boxes)):
                if 'phone' not in list_prior_chat_boxes[id].keys():
                    continue
                if list_prior_chat_boxes[id]['phone'] == num_send_phone_zalo:
                    name_ntd = list_prior_chat_boxes[id]['name']
                    pick = id
                    on_chat = True
                    break
            btn = d(resourceId="com.zing.zalo:id/action_bar_title")
            if btn.exists:
                current_ntd = btn.get_text()
                if current_ntd == name_ntd:
                    on_chat = True
                else:
                    while not d.xpath('//*[@text="Ưu tiên"]').exists:
                        d.press("back")
                        gvars.eventlet.sleep(0.1)
            if not on_chat:
                try:
                    while not d.xpath('//*[@text="Ưu tiên"]').exists:
                        if d.xpath('//*[@text="Zalo"]').exists:
                            try:
                                d.xpath(
                                    '//*[@text="Zalo"]').click()
                                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                    gvars.eventlet.sleep(0.05)
                            except Exception:
                                pass
                        else:
                            d.press("back")
                            gvars.eventlet.sleep(0.1)

                    d(text="Tìm kiếm").click()
                    gvars.eventlet.sleep(0.1)
                # gvars.time.sleep(1.0)
                    d.send_keys(f"{num_send_phone_zalo}", clear=True)

                    chat_num = d(
                        resourceId="com.zing.zalo:id/btn_search_result")
                    chat_num.click()

                    if d(resourceId="com.zing.zalo:id/btn_send_message").exists:
                        d(resourceId="com.zing.zalo:id/btn_send_message").click()
                    gvars.eventlet.sleep(0.2)
                    if d(textContains="Đóng").exists:
                        d(textContains="Đóng").click()
                        gvars.eventlet.sleep(0.5)
                    ntd = d(
                        resourceId="com.zing.zalo:id/action_bar_title")
                    name_ntd = ntd.get_text()
                    ntd.click()
                    gvars.eventlet.sleep(0.1)

                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    return gvars.jsonify({"status": "Bận rồi ông cháu ơi"})

                iv = d(
                    resourceId="com.zing.zalo:id/rounded_avatar_frame")
                gvars.eventlet.sleep(1.0)

                img = iv.screenshot()
                max_w, max_h = 200, 200
                img.thumbnail((max_w, max_h),
                              resample=gvars.Image.BILINEAR)
                buf = gvars.io.BytesIO()
                img.save(buf, format="JPEG",
                         optimize=True, quality=75)
                avatar_b64 = gvars.base64.b64encode(
                    buf.getvalue()).decode("ascii")

                if not already_sent_number(gvars.AVA_NUMBER_PATH):
                    ava_number = 0
                else:
                    ava_number = read_sent_number(gvars.AVA_NUMBER_PATH)
                with open(f"{gvars.IMAGE_FILE_DATA_PATH}/ava_{ava_number}.txt", "w", encoding="utf-8") as f:
                    f.write(avatar_b64)

                log_sent_number(ava_number+1, gvars.AVA_NUMBER_PATH)

                avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/ava_{ava_number}.txt"

                d.press('back')

                while not d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                    gvars.eventlet.sleep(0.05)

                # btn = d(resourceId="com.zing.zalo:id/tv_function_privacy")
                if d(text="Đã gửi lời mời kết bạn").exists:
                    friend_or_not = "added"
                else:
                    btn = d(
                        resourceId="com.zing.zalo:id/tv_function_privacy")
                    kb = d.xpath('//*[@text="Kết bạn"]')
                    if btn.exists or kb.exists:
                        friend_or_not = "no"
                    else:
                        friend_or_not = "yes"

                check = False
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name_ntd:
                        list_prior_chat_boxes[id]['phone'] = num_send_phone_zalo
                        list_prior_chat_boxes[id]['status'] = 'seen'
                        list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                        check = True
                        break
                if not check:
                    # list_prior_chat_boxes.append(
                    #    {"name": name_ntd, "phone": num_send_phone_zalo, "ava": avatar_64, "time": "", "friend_or_not": friend_or_not, "message": "", "status": "seen",  "data_chat_box": []})
                    gvars.dict_new_friend[num_phone_zalo][name_ntd] = {"phone": num_send_phone_zalo, "ava": avatar_64,
                                                                       "time": "", "friend_or_not": friend_or_not, "message": "", "status": "seen",  "data_chat_box": ""}
                if check:
                    data_update = {"num_phone_zalo": num_phone_zalo,
                                   "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                if not already_sent(num_send_phone_zalo):
                    log_sent(num_send_phone_zalo)

            else:
                list_friend = document['list_friend']
                for friend in list_friend:
                    if friend['name'] == name_ntd:
                        avatar_64 = friend['ava']
                        break
                friend_or_not = "no"
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name_ntd:
                        if 'friend_or_not' in list_prior_chat_boxes[id].keys():
                            friend_or_not = list_prior_chat_boxes[id]['friend_or_not']
                        # list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                        break
                # data_update = {"num_phone_zalo": num_phone_zalo,
                #               "list_prior_chat_boxes": list_prior_chat_boxes}
                # update_base_document_json(
                #    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
        except Exception as e:
            print(e)
            pass

        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)
        if device_status['active'] and len(gvars.dict_queue_device[id_device]) == 0:
            device_status['active'] = False
            print("Có set về false không")
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                gvars.json.dump(device_status, f, indent=4)

        gvars.dict_status_zalo[num_phone_zalo] = ""
        gvars.dict_status_update_pvp[num_phone_zalo] = 0
        del gvars.dict_queue_device[id_device][0]
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""
        return gvars.jsonify({"num_send_phone_zalo": num_send_phone_zalo, "name_ntd": name_ntd, "ava": avatar_64, "friend_or_not": friend_or_not}), 200


@gvars.app.route('/switch_account', methods=['POST', 'GET'])
def api_switch_account():

    data = gvars.request.form
    room = data.get('id_chat', '')
    num_phone_zalo = data.get('num_phone_zalo')
    num_send_phone_zalo = data.get('num_send_phone_zalo')
    one = gvars.time.time()
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    if gvars.dict_id_chat[id_device] != "" and gvars.dict_id_chat[id_device] != room:
        return gvars.jsonify({'status': "Thiết bị đang có người sử dụng"})
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    gvars.now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']

    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = gvars.dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if gvars.dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = gvars.dict_queue_device[id_device][0]
            gvars.eventlet.sleep(0.1)

        gvars.dict_status_update_pvp[num_phone_zalo] = 1
        gvars.dict_status_zalo[num_phone_zalo] = "switch_account"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:

            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = gvars.json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        gvars.json.dump(device_status, f, indent=4)
                    gvars.eventlet.sleep(0.2)
                d = gvars.u2.connect(id_device)
                d = switch_account(d, user_name)
                docs = get_base_id_zalo_json(
                    "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                for it in docs:
                    if it['status']:
                        current_phone = it['num_phone_zalo']
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})

                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = gvars.json.load(f)
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                if device_status['active'] and len(gvars.dict_queue_device[id_device]) == 0:
                    device_status['active'] = False
                    print("Có set về false không")
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        gvars.json.dump(device_status, f, indent=4)

                gvars.dict_status_zalo[num_phone_zalo] = ""
                gvars.dict_status_update_pvp[num_phone_zalo] = 0
                del gvars.dict_queue_device[id_device][0]

                return gvars.jsonify({"status": "Chuyển tài khoản thành công"})

            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                gvars.dict_status_zalo[num_phone_zalo] = ""
                gvars.dict_status_update_pvp[num_phone_zalo] = 0
                del gvars.dict_queue_device[id_device][0]
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                if device_status['active'] and len(gvars.dict_queue_device[id_device]) == 0:
                    device_status['active'] = False
                return gvars.jsonify({"status": "Chuyển tài khoản thất bại"})


@gvars.app.route('/api_add_friend_chat_pvp', methods=['POST', 'GET'])
def api_add_friend_chat_pvp():
    data = gvars.request.form
    gvars.list_socket_call.append("add_friend_chat_pvp")
    room = data.get('id_chat', '')
    num_phone_zalo = data.get('num_phone_zalo')
    name = data.get('name')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_add_friend
    global max_add_friend_per_day
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = gvars.json.load(f)

    for id in range(len(device_status['max_add_friend_per_day'])):
        if num_phone_zalo in device_status['max_add_friend_per_day'][id].keys():
            if device_status['max_add_friend_per_day'][id][num_phone_zalo] <= 0:
                return gvars.jsonify({"status": "Đã đạt giới hạn kết bạn một ngày"})
    if num_add_friend >= max_add_friend_per_day:
        return gvars.jsonify({"status": "Đã đạt giới hạn kết bạn một ngày"})
#    ava = data['ava']
    # gvars.dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        gvars.now_phone_zalo[id_device] = num_phone_zalo
    else:
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    if gvars.dict_id_chat[id_device] != "" and gvars.dict_id_chat[id_device] != room:
        return gvars.jsonify({'status': "Thiết bị đang có người sử dụng"})
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    # d = gvars.u2.connect(id_device)
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = gvars.dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if gvars.dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = gvars.dict_queue_device[id_device][0]
            gvars.eventlet.sleep(0.1)

        gvars.dict_status_update_pvp[num_phone_zalo] = 1
        gvars.dict_status_zalo[num_phone_zalo] = "add_friend_chat_pvp"

        try:
            d = gvars.u2.connect(id_device)
            gvars.device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối ", id_device)
            gvars.device_connect[id_device] = False
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})

        if not device_status['active']:
            device_status['active'] = True
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                gvars.json.dump(device_status, f, indent=4)
            gvars.eventlet.sleep(0.1)
            try:
                d.app_start("com.zing.zalo", stop=True)
                # gvars.eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    gvars.eventlet.sleep(0.05)
            except Exception as e:
                print("Thiết bị đã ngắt kết nối ", id_device)
                gvars.device_connect[id_device] = False
                gvars.dict_status_zalo[num_phone_zalo] = ""
                del gvars.dict_queue_device[id_device][0]
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})
                # if d is None:

        try:
            if d(text="Kết bạn").exists:
                d(resourceId="com.zing.zalo:id/tv_function_privacy").click()
                gvars.eventlet.sleep(1.0)
                d(resourceId="com.zing.zalo:id/btnSendInvitation").click()
                gvars.eventlet.sleep(1.0)
            else:
                gvars.dict_status_zalo[num_phone_zalo] = ""
                del gvars.dict_queue_device[id_device][0]
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                return gvars.jsonify({"status": "Đã gửi kết bạn trước đó hoặc đã là bạn bè"})

        except Exception as e:
            print("Lỗi gặp phải là: ", e)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            return gvars.jsonify({"status": "Gửi kết bạn thất bại"})

        check_add = False

        for id in range(len(list_prior_chat_boxes)):
            if list_prior_chat_boxes[id]['name'] == name:
                list_prior_chat_boxes[id]['friend_or_not'] = "added"
                check_add = True
                break
        if not check_add:
            if name in gvars.dict_new_friend[num_phone_zalo].keys:
                gvars.dict_new_friend[num_phone_zalo][name]['friend_or_not'] = "added"
        data_update = {"num_phone_zalo": num_phone_zalo,
                       "list_prior_chat_boxes": list_prior_chat_boxes}
        update_base_document_json(
            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

        num_add_friend += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)

        for id in range(len(device_status['max_add_friend_per_day'])):
            if num_phone_zalo in device_status['max_add_friend_per_day'][id].keys():
                device_status['max_add_friend_per_day'][id][num_phone_zalo] -= 1
                # handle_chat_view(d, num_phone_zalo)

        if device_status['active'] and len(gvars.dict_queue_device[id_device]) == 0:
            device_status['active'] = False

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            gvars.json.dump(device_status, f, indent=4)

        gvars.dict_status_zalo[num_phone_zalo] = ""
        del gvars.dict_queue_device[id_device][0]
        gvars.dict_status_update_pvp[num_phone_zalo] = 0
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""

        return gvars.jsonify({"status": "Gửi kết bạn thành công"})


@gvars.app.route('/api_create_group_chat_pvp', methods=['POST', 'GET'])
def api_add_create_group_chat_pvp():
    data = gvars.request.form
    gvars.list_socket_call.append("create_group_chat_pvp")
    num_phone_zalo = data.get('num_phone_zalo')
    name_group = data.get('name_group')
    mem_list_str = data.get('mem_list')
    room = data.get('id_chat', '')
    mem_list = gvars.json.loads(mem_list_str)
    # print("Danh sách thành viên nhóm là: ", mem_list)
    ava = data.get('group_avatar')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_add_friend
    global max_add_friend_per_day

    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = gvars.json.load(f)

    # ava = data.get('ava')
    # gvars.dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        gvars.now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
        # print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    if gvars.dict_id_chat[id_device] != "" and gvars.dict_id_chat[id_device] != room:
        return gvars.jsonify({'status': "Thiết bị đang có người sử dụng"})
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    list_group = document['list_group']
    try:
        d = gvars.u2.connect(id_device)
        gvars.device_connect[id_device] = True
    except Exception as e:
        print("Thiết bị đã ngắt kết nối ", id_device)
        gvars.device_connect[id_device] = False
        return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})

    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = gvars.dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if gvars.dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = gvars.dict_queue_device[id_device][0]
            gvars.eventlet.sleep(0.1)

        gvars.dict_status_update_pvp[num_phone_zalo] = 1
        gvars.dict_status_zalo[num_phone_zalo] = "create_group_chat_pvp"

        try:
            d = gvars.u2.connect(id_device)
            # global device_connect
            gvars.device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối ", id_device)
            gvars.device_connect[id_device] = False
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})

        if not device_status['active']:
            device_status['active'] = True
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                gvars.json.dump(device_status, f, indent=4)
            gvars.eventlet.sleep(0.2)
            try:
                d.app_start("com.zing.zalo", stop=True)
                # gvars.eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    gvars.eventlet.sleep(0.05)
            except Exception as e:
                print("Thiết bị đã ngắt kết nối ", id_device)
                gvars.device_connect[id_device] = False
                gvars.dict_status_zalo[num_phone_zalo] = ""
                del gvars.dict_queue_device[id_device][0]
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                return gvars.jsonify({"status": "Thiết bị đã ngắt kết nối"})
                # if d is None:

        try:
            d.app_start("com.zing.zalo", stop=True)
            gvars.eventlet.sleep(1.0)
            d(resourceId="com.zing.zalo:id/action_bar_plus_btn").click()
            gvars.eventlet.sleep(0.1)
            d(text="Tạo nhóm").click()
            gvars.eventlet.sleep(0.1)
            if name_group != "":
                gr_names = [group['name'] for group in list_group]
                if name_group in gr_names:
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    return gvars.jsonify({"status": "Tên nhóm này tồn tại, yêu cầu đặt tên khác"})
                try:
                    d.xpath(
                        '//*[@resource-id="com.zing.zalo:id/header_section"]/android.widget.LinearLayout[1]').click()
                except Exception as e:
                    d.xpath(
                        '//*[@resource-id="com.zing.zalo:id/layout_update_avatar"]/android.widget.LinearLayout[1]').click()
                gvars.eventlet.sleep(0.1)
                d.send_keys(name_group, clear=True)
                gvars.eventlet.sleep(0.1)
                d(resourceId="com.zing.zalo:id/btn_done_input_group_name").click()
                gvars.eventlet.sleep(0.1)
            else:
                if len(mem_list) > 2:
                    name_group = ", ".join(mem_list[:2])
                else:
                    name_group = ", ".join(mem_list)
            avatar = ava
            if ava != "":
                pass
            print("Danh sách thành viên là: ", mem_list)
            for mem in mem_list:
                d(resourceId="com.zing.zalo:id/edt_search").click()
                gvars.eventlet.sleep(0.1)
                d.send_keys(mem, clear=True)
                gvars.eventlet.sleep(0.1)
                # if d(textContains=mem).exists:
                #    d(textContains=mem).click()
                el = d.xpath(
                    '//android.widget.FrameLayout[@index="0" and normalize-space(@text) != ""]')
                if el.exists:
                    el.click()
                    gvars.eventlet.sleep(0.1)

            d(resourceId="com.zing.zalo:id/btn_done_create_group").click()
            gvars.eventlet.sleep(1.0)

            if d(resourceId="com.zing.zalo:id/btn_done_create_group").exists:
                gvars.dict_status_zalo[num_phone_zalo] = ""
                try:
                    d.press('back')
                    gvars.eventlet.sleep(0.1)
                    d.xpath(
                        '//*[@resource-id="com.zing.zalo:id/modal_cta_custom_layout"]/android.widget.RelativeLayout[2]').click()
                    gvars.eventlet.sleep(0.1)
                except Exception as e:
                    print("Lỗi gặp phải là: ", e)
                return gvars.jsonify({"status": "Cần tối thiểu 1 người là bạn bè"})

            list_mems = [{"name_member": user_name, "role": "Trưởng nhóm"}]
            for mem in mem_list:
                list_mems.append({"name_member": mem, "role": ""})
            check_mems = True

            list_prior_chat_boxes.append({"name": name_group, "phone": "", "ava": avatar, "time": "", "message": "",
                                         "status": "seen", "data_chat_box": "", "list_mems": list_mems, "check_mems": check_mems})
            list_prior_chat_boxes.insert(
                0, list_prior_chat_boxes.pop(-1))
            list_group.append(
                {"name": name_group, "ava": avatar, "list_mems": list_mems, "check_mems": check_mems})
        except Exception as e:
            print("Lỗi gặp phải là: ", e)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            try:
                d.press('back')
                gvars.eventlet.sleep(0.1)
                d.xpath(
                    '//*[@resource-id="com.zing.zalo:id/modal_cta_custom_layout"]/android.widget.RelativeLayout[2]').click()
                gvars.eventlet.sleep(0.1)
            except Exception as e:
                print("Lỗi gặp phải là: ", e)
            return gvars.jsonify({"status": "Tạo nhóm thất bại"})

        data_update = {"num_phone_zalo": num_phone_zalo,
                       "list_prior_chat_boxes": list_prior_chat_boxes, "list_group": list_group}
        update_base_document_json(
            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)

        if device_status['active'] and len(gvars.dict_queue_device[id_device]) == 0:
            device_status['active'] = False
            # print("Có set về false không")
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                gvars.json.dump(device_status, f, indent=4)

        gvars.dict_status_zalo[num_phone_zalo] = ""
        del gvars.dict_queue_device[id_device][0]
        gvars.dict_status_update_pvp[num_phone_zalo] = 0
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""

        return gvars.jsonify({"status": "Tạo nhóm thành công"})
