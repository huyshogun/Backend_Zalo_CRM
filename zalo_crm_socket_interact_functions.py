import zalo_crm_global_variables as gvars
from zalo_crm_crud_database import get_base_id_zalo_json, update_base_document_json, already_sent, log_sent
from zalo_crm_other_functions import handle_chat_view, load_data_chat_box_json, dump_data_chat_box_json

max_message_per_day = 300
num_message = 0
num_add_friend = 0
image_number = 300
max_add_friend_per_day = 30

@gvars.socketio.on('connect')
def handle_connect():
    gvars.list_socket_call.append("connect")
    print(f"Client connected: {gvars.request.sid}")
    # while True:
    #     print ("list_socket_call ----", list_socket_call)
    #     gvars.eventlet.sleep(2)


@gvars.socketio.on('join')
def handle_join(data):
    gvars.list_socket_call.append("join")
    global id_chat
    room = data['id_chat']
    id_chat = room
    # global folder_data_zalo
    # folder_data_zalo = data['folder_data_zalo']
    # os.makedirs(os.path.join(folder_data_zalo, 'data'), exist_ok=True)
    gvars.join_room(room)
    # print(f"Client {gvars.request.sid} joined room {room}")
    # res =  update_port_base_id_chat("C:/Zalo_CRM/Zalo_base", "Zalo_data_login_port",room)
    gvars.emit("status_update_list_chat", {"status": "1"}, room=room)
    # print ("update_port_base_id_chat------------------", res )


@gvars.socketio.on('leave')
def handle_leave(data):
    gvars.list_socket_call.append("leave")
    room = data['id_chat']
    gvars.leave_room(room)
    print(f"Client {gvars.request.sid} left room {room}")


@gvars.socketio.on('open_chat_pvp')
def handle_chat_pvp(data):
    gvars.list_socket_call.append("open_chat_pvp")
    room = data['id_chat']
    num_phone_zalo = data['num_phone_zalo']
    num_send_phone_zalo = data['num_send_phone_zalo']
    name = data['name']
#    ava = data['ava']
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
        gvars.join_room(room)
        gvars.emit("receive_device_status", {
            "status": "Thiết bị đang có người sử dụng", 'name_ntd': name}, room=room)
        return False
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    gvars.now_phone_zalo[id_device] = num_phone_zalo
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    list_friend = document['list_friend']

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
        gvars.dict_status_zalo[num_phone_zalo] = "handle_chat_pvp"

        try:
            d = gvars.u2.connect(id_device)
            # global device_connect
            gvars.device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            gvars.device_connect[id_device] = False
            gvars.join_room(room)
            gvars.emit("receive_device_status", {
                "status": "Thiết bị đã ngắt kết nối", 'name_ntd': name}, room=room)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return False
        try:
            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                device_status = gvars.json.load(f)
            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    gvars.json.dump(device_status, f, indent=4)
                gvars.eventlet.sleep(0.2)
                d.app_start("com.zing.zalo", stop=True)
                # gvars.eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    gvars.eventlet.sleep(0.05)
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            gvars.device_connect[id_device] = False
            gvars.join_room(room)
            gvars.emit("receive_device_status", {
                "status": "Thiết bị đã ngắt kết nối", 'name_ntd': name}, room=room)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return False

        try:
            if num_phone_zalo in gvars.dict_new_friend.keys():
                if name in gvars.dict_new_friend[num_phone_zalo].keys():
                    num_send_phone_zalo = gvars.dict_new_friend[num_phone_zalo][name]['phone']

            if num_send_phone_zalo != "":
                name_ntd = ""
                # pick = ""
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['phone'] == num_send_phone_zalo:
                        name_ntd = list_prior_chat_boxes[id]['name']
                        # pick = id
                        break
                on_chat = False
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
                    items = d.xpath(
                        "//android.widget.FrameLayout[@text!='']").all()
                    check_ex = False
                    for item in items:
                        raw = item.text
                        lines = [l for l in raw.split(
                            "\n") if l.strip()]
                        if lines[0] == name_ntd:
                            try:
                                item.click()
                                check_ex = True
                            except Exception as e:
                                print(e)
                            break
                    if not check_ex:
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            if d.xpath('//*[@text="Zalo"]').exists:
                                # try:
                                d.xpath(
                                    '//*[@text="Zalo"]').click()
                                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                    gvars.eventlet.sleep(0.05)
                                # except Exception:
                                #    pass
                            else:
                                d.press("back")
                                gvars.eventlet.sleep(0.1)
                        # d.app_start("com.zing.zalo", stop=True)
                        # d = run_start(d)
                        try:

                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(0.1)
                            d.send_keys(
                                f"{num_send_phone_zalo}", clear=True)
                        except Exception as e:
                            print(e)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            gvars.emit("receive_chat_view_status", {
                                "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False

                        try:
                            chat_num = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            chat_num.click()

                        except Exception:
                            gvars.emit("receive_chat_view_status", {
                                "status": "Số điện thoại chưa tạo tài khoản zalo", "name_ntd": name}, room=room)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                gvars.eventlet.sleep(0.1)
                        except Exception:
                            pass

                    try:
                        if d(textContains="Đóng").exists:
                            d(textContains="Đóng").click()
                            gvars.eventlet.sleep(0.5)
                        name_ntd = d(
                            resourceId="com.zing.zalo:id/action_bar_title").get_text()
                    except Exception as e:
                        print(e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_chat_view_status", {
                            "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                        return False
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

                    # for id in range(len(list_friend)):
                    ck_add_or_dl = False

                    if friend_or_not == 'yes':
                        fr_name = [l['name'] for l in list_friend]
                        if name_ntd not in fr_name:
                            ava = ""
                            if name_ntd in gvars.dict_new_friend[num_phone_zalo].keys:
                                ava = gvars.dict_new_friend[num_phone_zalo][name]['ava']
                            list_friend.append(
                                {"name": name_ntd, "ava": ava, "phone": num_send_phone_zalo})
                            ck_add_or_dl = True
                    elif friend_or_not == 'no':
                        for id in range(len(list_friend)):
                            if list_friend[id]['name'] == name_ntd:
                                del list_friend[id]
                                ck_add_or_dl = True

                    if not check:
                        if name_ntd in gvars.dict_new_friend[num_phone_zalo].keys:
                            if friend_or_not == 'added':
                                gvars.dict_new_friend[num_phone_zalo][name_ntd]['friend_or_not'] = "added"

                    if ck_add_or_dl:
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_prior_chat_boxes": list_prior_chat_boxes, "list_friend": list_friend}
                    else:
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name_ntd:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'
                                data_update = {"num_phone_zalo": num_phone_zalo,
                                               "list_prior_chat_boxes": list_prior_chat_boxes}
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                            break
                gvars.join_room(room)
                # gvars.emit("receive_chat_view_status",{"status":"Cuộc hội thoại bắt đầu", "name_ntd": name_ntd}, room=room)
                if not already_sent(num_send_phone_zalo):
                    log_sent(num_send_phone_zalo)
                print("Cuộc hội thoại bắt đầu")
                gvars.emit("receive_chat_view_status", {
                    "status": "Cuộc hội thoại bắt đầu"}, room=room)

            else:
                on_chat = False
                btn = d(resourceId="com.zing.zalo:id/action_bar_title")
                if btn.exists:
                    current_ntd = btn.get_text()
                    print(current_ntd)
                    if current_ntd == name:
                        on_chat = True
                    else:
                        # d.press("back")
                        # if d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                        #    d.press("back")
                        #    gvars.eventlet.sleep(0.1)
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            d.press("back")
                            gvars.eventlet.sleep(0.1)
                if not on_chat:
                    items = d.xpath(
                        "//android.widget.FrameLayout[@text!='']").all()
                    check_ex = False
                    for item in items:
                        raw = item.text
                        lines = [l for l in raw.split(
                            "\n") if l.strip()]
                        if lines[0] == name:
                            item.click()
                            check_ex = True
                            break
                    if not check_ex:
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            if d.xpath('//*[@text="Zalo"]').exists:
                                # try:
                                d.xpath(
                                    '//*[@text="Zalo"]').click()
                                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                    gvars.eventlet.sleep(0.05)
                                # except Exception:
                                #    pass
                            else:
                                d.press("back")
                                gvars.eventlet.sleep(0.1)

                        try:
                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(0.1)
                        except Exception as e:
                            print(e)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            gvars.emit("receive_chat_view_status", {
                                "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False
                        # gvars.time.sleep(1.0)
                        d.send_keys(f"{name}", clear=True)
                        gvars.eventlet.sleep(0.15)

                        try:

                            chat_list = d.xpath(
                                '//*[@resource-id="com.zing.zalo:id/btn_search_result"]').all()

                            ck_ex = False

                            # if len(chat_num) > 0:
                            for item in chat_list:
                                raw = item.text
                                print("Raw là", raw)
                                lines = [l for l in raw.split(
                                    "\n") if l.strip()]
                                print(lines)
                                if lines[0] == name:
                                    print("Có trùng khớp")
                                    item.click()
                                    ck_ex = True
                                    break
                            gvars.eventlet.sleep(0.1)

                            if not ck_ex:
                                for id in range(len(list_prior_chat_boxes)):
                                    if list_prior_chat_boxes[id]['name'] == name:
                                        del list_prior_chat_boxes[id]
                                        data_update = {"num_phone_zalo": num_phone_zalo,
                                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                                        update_base_document_json(
                                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                        break

                                for id in range(len(list_friend)):
                                    if list_friend[id]['name'] == name:
                                        del list_friend[id]
                                        data_update = {"num_phone_zalo": num_phone_zalo,
                                                       "list_friend": list_friend}
                                        update_base_document_json(
                                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                        break

                                gvars.emit("receive status", {
                                    "status": "Tài khoản không tồn tại"}, room=room)
                                gvars.dict_status_zalo[num_phone_zalo] = ""
                                del gvars.dict_queue_device[id_device][0]
                                if len(gvars.dict_queue_device[id_device]) == 0:
                                    gvars.dict_id_chat[id_device] = ""
                                print("Tài khoản không tồn tại")
                                return False

                        except Exception:
                            gvars.emit("receive status", {
                                "status": "Tài khoản không tồn tại"}, room=room)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            print("Có lỗi à cậu")
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                gvars.eventlet.sleep(0.5)
                        except Exception:
                            print("Lỗi có ở đây không")
                            pass

                    check = False
                    check_seen = False
                    check_add_friend = False
                    if d(text="Đã gửi lời mời kết bạn").exists:
                        friend_or_not = "added"
                        print("Đã gửi lời mời kết bạn")
                    else:
                        btn = d(
                            resourceId="com.zing.zalo:id/tv_function_privacy")
                        kb = d.xpath('//*[@text="Kết bạn"]')
                        if btn.exists or kb.exists:
                            print("chưa kết bạn")
                            friend_or_not = "no"
                        else:
                            friend_or_not = "yes"
                            print("Dẫ kết bạn")

                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                check_seen = True
                            list_prior_chat_boxes[id]['status'] = 'seen'
                            if 'friend_or_not' not in list_prior_chat_boxes[id].keys():
                                check_add_friend = True
                                list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                            else:
                                if list_prior_chat_boxes[id]['friend_or_not'] != friend_or_not:
                                    list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                                    check_add_friend = True
                            check = True
                            # check_add_friend = True
                            break

                    ck_add_or_dl = False

                    if friend_or_not == 'yes':
                        fr_name = [l['name'] for l in list_friend]
                        if name not in fr_name:
                            ava = ""
                            if name in gvars.dict_new_friend[num_phone_zalo].keys:
                                ava = gvars.dict_new_friend[num_phone_zalo][name]['ava']
                            list_friend.append(
                                {"name": name, "ava": ava, "phone": num_send_phone_zalo})
                            ck_add_or_dl = True
                    elif friend_or_not == 'no':
                        for id in range(len(list_friend)):
                            if list_friend[id]['name'] == name:
                                del list_friend[id]
                                ck_add_or_dl = True

                    if not check:
                        if name in gvars.dict_new_friend[num_phone_zalo].keys:
                            if friend_or_not == 'added':
                                gvars.dict_new_friend[num_phone_zalo][name]['friend_or_not'] = "added"

                    if not check or check_seen or check_add_friend or ck_add_or_dl:
                        if ck_add_or_dl:
                            data_update = {"num_phone_zalo": num_phone_zalo,
                                           "list_prior_chat_boxes": list_prior_chat_boxes, "list_friend": list_friend}
                        else:
                            data_update = {"num_phone_zalo": num_phone_zalo,
                                           "list_prior_chat_boxes": list_prior_chat_boxes}
                        update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'
                                data_update = {"num_phone_zalo": num_phone_zalo,
                                               "list_prior_chat_boxes": list_prior_chat_boxes}
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                            break

                gvars.join_room(room)
                # gvars.emit("receive status",{"status":"Cuộc hội thoại bắt đầu"}, room=room)
                print("Cuộc hội thoại bắt đầu")
                gvars.emit("receive_chat_view_status", {
                    "status": "Cuộc hội thoại bắt đầu"}, room=room)
        except Exception as e:
            print(e)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return False

        gvars.dict_status_zalo[num_phone_zalo] = ""
        del gvars.dict_queue_device[id_device][0]
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""

        gvars.dict_status_update_pvp[num_phone_zalo] = 2
        handle_chat_view(d, num_phone_zalo)
        return True


@gvars.socketio.on('send_message_chat_pvp')
def handle_send_message_chat_pvp(data):
    gvars.list_socket_call.append("send_message_chat_pvp")
#    room = data["id_chat"]
    room = data['id_chat']
    num_phone_zalo = data['num_phone_zalo']
    # num_send_phone_zalo = data['num_send_phone_zalo']
    message = data['message']
    name = data['name']
    type = data['type']
    name_card = data['name_card']
    num_phone_card = data['num_phone_card']
    # mime = data['mime']
    image_data = data['image_data']
    file_size = data['file_size']
    file_data = data['file_data']
    file_type = data['file_type']
    file_name = data['file_name']
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_message
    global max_message_per_day
    global image_number
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = gvars.json.load(f)

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
        gvars.join_room(room)
        gvars.emit("receive_device_status", {
            "status": "Thiết bị đang có người sử dụng", 'name_ntd': name}, room=room)
        return False
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    list_friend = document['list_friend']
    # d = gvars.u2.connect(id_device)
    for id in range(len(device_status['max_message_per_day'])):
        if num_phone_zalo in device_status['max_message_per_day'][id].keys():
            if device_status['max_message_per_day'][id][num_phone_zalo] <= 0:
                gvars.join_room(room)
                gvars.emit(
                    "receive status", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
                return False

    if num_message >= max_message_per_day:
        gvars.emit(
            "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
        return False
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

        gvars.dict_status_zalo[num_phone_zalo] = "send_message_chat_pvp"
        # with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        #    device_status = gvars.json.load(f)
        try:
            try:
                d = gvars.u2.connect(id_device)
                gvars.device_connect[id_device] = True
            except Exception as e:
                print("Thiết bị đã ngắt kết nối ", id_device)
                gvars.device_connect[id_device] = False
                gvars.join_room(room)
                gvars.emit("receive_device_status", {
                    "status": "Thiết bị đã ngắt kết nối", 'name_ntd': name}, room=room)
                gvars.dict_status_zalo[num_phone_zalo] = ""
                del gvars.dict_queue_device[id_device][0]
                if len(gvars.dict_queue_device[id_device]) == 0:
                    gvars.dict_id_chat[id_device] = ""
                return False
            if not device_status['active'] or not d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    gvars.json.dump(device_status, f, indent=4)
                gvars.eventlet.sleep(0.1)
                try:
                    d.app_start("com.zing.zalo", stop=True)
                    while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                        gvars.eventlet.sleep(0.05)
                except Exception as e:
                    print("Thiết bị đã ngắt kết nối ", id_device)
                    gvars.device_connect[id_device] = False
                    gvars.join_room(room)
                    gvars.emit("receive_device_status", {
                        "status": "Thiết bị đã ngắt kết nối", 'name_ntd': name}, room=room)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    return False

                # gvars.eventlet.sleep(1.0)
                try:
                    items = d.xpath(
                        "//android.widget.FrameLayout[@text!='']").all()
                    check_ex = False
                    for item in items:
                        raw = item.text
                        lines = [l for l in raw.split(
                            "\n") if l.strip()]
                        if lines[0] == name:
                            item.click()
                            check_ex = True
                            break
                    if not check_ex:
                        try:
                            d(text="Tìm kiếm").click_exists(
                                timeout=1)
                        except Exception as e:
                            print(e)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            gvars.emit("receive_chat_view_status", {
                                "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False

                        d.send_keys(f"{name}", clear=True)
                        gvars.eventlet.sleep(0.15)

                        try:
                            chat_list = d.xpath(
                                '//*[@resource-id="com.zing.zalo:id/btn_search_result"]').all()

                            ck_ex = False
                            # if len(chat_num) > 0:
                            for item in chat_list:
                                raw = item.text
                                print("Raw là", raw)
                                lines = [l for l in raw.split(
                                    "\n") if l.strip()]
                                print(lines)
                                if lines[0] == name:
                                    print("Có trùng khớp")
                                    item.click()
                                    ck_ex = True
                                    break
                            gvars.eventlet.sleep(0.5)
                            if not ck_ex:
                                for id in range(len(list_prior_chat_boxes)):
                                    if list_prior_chat_boxes[id]['name'] == name:
                                        del list_prior_chat_boxes[id]
                                        data_update = {"num_phone_zalo": num_phone_zalo,
                                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                                        update_base_document_json(
                                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                        break

                                for id in range(len(list_friend)):
                                    if list_friend[id]['name'] == name:
                                        del list_friend[id]
                                        data_update = {"num_phone_zalo": num_phone_zalo,
                                                       "list_friend": list_friend}
                                        update_base_document_json(
                                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                        break

                                gvars.emit("receive status", {
                                    "status": "Tài khoản không tồn tại"}, room=room)
                                gvars.dict_status_zalo[num_phone_zalo] = ""
                                del gvars.dict_queue_device[id_device][0]
                                if len(gvars.dict_queue_device[id_device]) == 0:
                                    gvars.dict_id_chat[id_device] = ""
                                print("Tài khoản không tồn tại")
                                return False

                        except Exception:
                            gvars.emit("receive status", {
                                "status": "Tài khoản không tồn tại"}, room=room)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            print("Có lỗi à cậu")
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                gvars.eventlet.sleep(0.5)
                            if d(textContains="Đóng").exists:
                                d(textContains="Đóng").click()
                                gvars.eventlet.sleep(0.5)
                        except Exception:
                            print("Lỗi có ở đây không")
                            pass
                except Exception as e:
                    print(e)
                # if d is None:

            if type == 'image':
                avatar = gvars.base64.b64decode(image_data)
                with open(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg', 'wb') as f:
                    f.write(avatar)
                print(
                    f"Đã lưu vào thư mục Zalo_base/image{image_number}.jpg")
                d.push(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg',
                       f'/sdcard/Download/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                gvars.eventlet.sleep(0.1)
                image_number -= 1
                '''
                    if id_device in special_device:
                        try:
                           d(resourceId="com.zing.zalo:id/new_chat_input_btn_show_gallery").click_exists(timeout=3)
                           d.xpath('//*[@resource-id="com.zing.zalo:id/recycler_view"]/android.widget.FrameLayout[2]').click_exists(timeout=3)
                           #d(resourceId="com.zing.zalo:id/new_chat_input_btn_send_media").click_exists(timeout=3)
                           d(resourceId="com.zing.zalo:id/landing_page_layout_send").click_exists(timeout=3)
                        except Exception as e:
                            print(e)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                            return False 
                    '''
                # if id_device in special_device:

                try:
                  # if id_device not in special_device:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    d.xpath(
                        '//*[@text="Tài liệu"]').click()
                    gvars.eventlet.sleep(1)

                    if d.xpath('//*[@text="Gần đây"]').exists:
                        d(description="Hiển thị gốc").click_exists(
                            timeout=3)
                        gvars.eventlet.sleep(0.2)
                        td = d.xpath('//*[@text="Tệp đã tải xuống"]')
                        if td.exists:
                            td.click()
                            gvars.eventlet.sleep(0.1)
                        else:
                            if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                d(resourceId="android:id/title",
                                  text="Tệp đã tải xuống").click()
                                # gvars.eventlet.sleep(0.1)
                            else:
                                d.xpath(
                                    '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                        gvars.eventlet.sleep(0.1)
                    click_btn = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                    if click_btn.exists:
                        click_btn.click_exists(timeout=0.1)
                        gvars.eventlet.sleep(0.1)
                    btn1 = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                    btn2 = d(
                        resourceId="com.google.android.documentsui:id/item_root")
                    if btn1.exists:
                        btn1.click()
                        gvars.eventlet.sleep(0.1)
                    elif btn2.exists:
                        btn2.click()
                        gvars.eventlet.sleep(0.1)
                    if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        # pass
                    else:
                        # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                        d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    gvars.emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False
            elif type == 'file':
                file_decode = gvars.base64.b64decode(file_data)

                with open(f'C:/Zalo_CRM/Zalo_base/{file_name}', 'wb') as f:
                    f.write(file_decode)
                d.push(f'C:/Zalo_CRM/Zalo_base/{file_name}',
                       f'/sdcard/Download/{file_name}')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                gvars.eventlet.sleep(0.1)
                # image_number -= 1
                try:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    d.xpath(
                        '//*[@text="Tài liệu"]').click()
                    gvars.eventlet.sleep(1)

                    if d.xpath('//*[@text="Gần đây"]').exists:
                        d(description="Hiển thị gốc").click_exists(
                            timeout=3)
                        gvars.eventlet.sleep(0.2)
                        td = d.xpath('//*[@text="Tệp đã tải xuống"]')
                        if td.exists:
                            td.click()
                            gvars.eventlet.sleep(0.1)
                        else:
                            if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                d(resourceId="android:id/title",
                                  text="Tệp đã tải xuống").click()
                                # gvars.eventlet.sleep(0.1)
                            else:
                                d.xpath(
                                    '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                        gvars.eventlet.sleep(0.1)
                    click_btn = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                    if click_btn.exists:
                        click_btn.click_exists(timeout=0.1)
                        gvars.eventlet.sleep(0.1)
                    btn1 = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                    btn2 = d(
                        resourceId="com.google.android.documentsui:id/item_root")
                    if btn1.exists:
                        btn1.click()
                    elif btn2.exists:
                        btn2.click()
                    if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        # pass
                    else:
                        # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                        d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    gvars.emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False

            elif type == 'text':

                try:
                    d(resourceId="com.zing.zalo:id/chatinput_text").click()
                    gvars.eventlet.sleep(0.1)
                    d.send_keys(message, clear=True)
                    gvars.eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    gvars.emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False
            elif type == 'card':
                try:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    gvars.eventlet.sleep(0.1)
                    d.xpath('//*[@text="Danh thiếp"]').click()
                    gvars.eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/search_input_text").click()
                    gvars.eventlet.sleep(0.1)
                    d.send_keys(name_card, clear=True)
                    gvars.eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/layoutcontact").click()
                    gvars.eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/btn_done_add_item").click()
                    gvars.eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    gvars.eventlet.sleep(0.1)
                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""
                    del gvars.dict_queue_device[id_device][0]
                    if len(gvars.dict_queue_device[id_device]) == 0:
                        gvars.dict_id_chat[id_device] = ""
                    gvars.emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False

            now = gvars.datetime.now()
            print("Ngày:", now.day)
            print("Tháng:", now.month)
            print("Năm:", now.year)
            print("Giờ:", now.hour)
            print("Phút:", now.minute)
            print("Giây:", now.second)
            hour = str(now.hour)
            minute = str(now.hour)
            if len(hour) == 1:
                hour = f"0{hour}"
            if len(minute) == 1:
                minute = f"0{minute}"
            time_str = f"{hour}:{minute} {now.day}/{now.month}/{now.year}"
            gvars.eventlet.sleep(1.0)
            gvars.join_room(room)
            check = False
            # pick = -1
            for id in range(len(list_prior_chat_boxes)):
                if list_prior_chat_boxes[id]['name'] == name:
                    check = True
                    if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                        list_prior_chat_boxes[id]['data_chat_box'] = ""
                    if type == 'text':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "text", "data": message}]})
                        list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'image':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                        list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'file':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                        list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'card':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "card", "data": f"{name_card}\nGọi điện\nNhắn tin", "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                        list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    break

                    # pick = id
            if not check:
                data_chat_box = []
                ava = ""
                phone = ""
                friend_or_not = "no"
                if name in gvars.dict_new_friend[num_phone_zalo].keys():
                    ava = gvars.dict_new_friend[num_phone_zalo][name]['ava']
                    phone = gvars.dict_new_friend[num_phone_zalo][name]['phone']
                    friend_or_not = gvars.dict_new_friend[num_phone_zalo][name]['friend_or_not']
                    del gvars.dict_new_friend[num_phone_zalo][name]
                if type == 'text':
                    list_prior_chat_boxes.append(
                        {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": message, "status": "seen", "data_chat_box": ""})
                    data_chat_box = load_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'])
                    data_chat_box.append(
                        {"you": [{'time': time_str, 'type': "text", "data": message}]})
                    list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'image':
                    list_prior_chat_boxes.append(
                        {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": f"image{image_number+1}.jpg", "status": "seen", "data_chat_box": ""})
                    data_chat_box = load_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'])
                    data_chat_box.append(
                        {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                    list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'file':
                    list_prior_chat_boxes.append(
                        {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": f"[File]\n{file_name}\n{file_size}", "status": "seen", "data_chat_box": ""})
                    data_chat_box = load_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'])
                    data_chat_box.append(
                        {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                    list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'card':
                    list_prior_chat_boxes.append(
                        {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": message, "status": "seen", "data_chat_box": ""})
                    data_chat_box = load_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'])
                    data_chat_box.append(
                        {"you": [{'time': time_str, 'type': "card", "data": message, "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                    list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))

            data_update = {"num_phone_zalo": num_phone_zalo,
                           "list_prior_chat_boxes": list_prior_chat_boxes}
            update_base_document_json(
                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
            if type == 'card':
                gvars.emit("receive status", {
                    "status": "Đã gửi tin nhắn thành công"}, room=room)
            gvars.emit('receive_list_prior_chat_box', {
                'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, room=room)
        except Exception as e:
            print(e)
            gvars.emit("receive status", {
                "status": "Đã gửi tin nhắn thất bại"}, room=room)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            gvars.dict_status_update_pvp[num_phone_zalo] = 2
            handle_chat_view(d, num_phone_zalo)
            return False
        num_message += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)

        for id in range(len(device_status['max_message_per_day'])):
            if num_phone_zalo in device_status['max_message_per_day'][id].keys():
                device_status['max_message_per_day'][id][num_phone_zalo] -= 1

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            gvars.json.dump(device_status, f, indent=4)

        gvars.dict_status_zalo[num_phone_zalo] = ""
        gvars.dict_status_update_pvp[num_phone_zalo] = 2
        del gvars.dict_queue_device[id_device][0]
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""
        # two = time.time()
        # print(two-one)
        handle_chat_view(d, num_phone_zalo)


@gvars.socketio.on('share_message_chat_pvp')
def handle_share_message_chat_pvp(data):
    gvars.list_socket_call.append("share_message_chat_pvp")
#    room = data["id_chat"]
    room = data['id_chat']
    # print("helloo every one")
    num_phone_zalo = data['num_phone_zalo']
    # num_send_phone_zalo = data['num_send_phone_zalo']
    message = data['message']
    names = data['names']
    name_share = data['name_share']
    name_card = data['name_card']
    num_phone_card = data['num_phone_card']
    extra_message = data['extra_message']
    type = data['type']
    # mime = data['mime']
    image_data = data['image_data']
    file_size = data['file_size']
    file_data = data['file_data']
    file_type = data['file_type']
    file_name = data['file_name']
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_message
    global max_message_per_day
    global image_number

    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = gvars.json.load(f)

    for id in range(len(device_status['max_message_per_day'])):
        if num_phone_zalo in device_status['max_message_per_day'][id].keys():
            if device_status['max_message_per_day'][id][num_phone_zalo] <= 0:
                gvars.emit(
                    "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
                return False

    if num_message >= max_message_per_day:
        gvars.emit(
            "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
        return False
#    ava = data['ava']
    # gvars.dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
    else:
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    if gvars.dict_id_chat[id_device] != "" and gvars.dict_id_chat[id_device] != room:
        gvars.join_room(room)
        gvars.emit("receive_device_status", {
            "status": "Thiết bị đang có người sử dụng", 'name_ntd': name}, room=room)
        return False
    gvars.dict_id_chat[id_device] = room
    gvars.dict_process_id[id_device] += 1
    id_process = gvars.dict_process_id[id_device]
    gvars.dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    list_friend = document['list_friend']
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

        gvars.dict_status_zalo[num_phone_zalo] = "share_message_chat_pvp"
#                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
#                    device_status = gvars.json.load(f)
        try:
            d = gvars.u2.connect(id_device)
            gvars.device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối ", id_device)
            gvars.device_connect[id_device] = False
            gvars.join_room(room)
            gvars.emit("receive_device_status", {
                "status": "Thiết bị đã ngắt kết nối", 'name_ntd': name}, room=room)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            return False
        try:

            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    gvars.json.dump(device_status, f, indent=4)
                gvars.eventlet.sleep(0.1)
                d.app_start("com.zing.zalo", stop=True)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    gvars.eventlet.sleep(0.05)

            if type == 'image':
                avatar = gvars.base64.b64decode(image_data)
                with open(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg', 'wb') as f:
                    f.write(avatar)
                print(
                    f"Đã lưu vào thư mục Zalo_base/image{image_number}.jpg")
                d.push(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg',
                       f'/sdcard/Download/image{image_number}.jpg')
            elif type == 'file':
                file_decode = gvars.base64.b64decode(file_data)
                with open(f'C:/Zalo_CRM/Zalo_base/{file_name}', 'wb') as f:
                    f.write(file_decode)
                d.push(f'C:/Zalo_CRM/Zalo_base/{file_name}',
                       f'/sdcard/Download/{file_name}')
            for name in names:

                on_chat = False
                btn = d(resourceId="com.zing.zalo:id/action_bar_title")
                if btn.exists:
                    current_ntd = btn.get_text()

                    if current_ntd == name:
                        on_chat = True
                    else:
                        try:
                            # d.press("back")
                            # if d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                            #    d.press("back")
                            while not d.xpath('//*[@text="Ưu tiên"]').exists:
                                d.press("back")
                                gvars.eventlet.sleep(0.1)
                        except Exception as e:
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            print(e)
                            return False
                if not on_chat:
                    try:
                        items = d.xpath(
                            "//android.widget.FrameLayout[@text!='']").all()
                        check_ex = False
                        for item in items:
                            raw = item.text
                            lines = [l for l in raw.split(
                                "\n") if l.strip()]
                            if lines[0] == name:
                                item.click()
                                check_ex = True
                                break
                        if not check_ex:
                            while not d.xpath('//*[@text="Ưu tiên"]').exists:
                                if d.xpath('//*[@text="Zalo"]').exists:
                                    try:
                                        d.xpath(
                                            '//*[@text="Zalo"]').click()
                                        gvars.eventlet.sleep(1.5)
                                    except Exception:
                                        pass
                                else:
                                    d.press("back")

                            try:
                                d(text="Tìm kiếm").click()

                            except Exception as e:
                                print(e)
                                gvars.dict_status_zalo[num_phone_zalo] = ""
                                del gvars.dict_queue_device[id_device][0]
                                if len(gvars.dict_queue_device[id_device]) == 0:
                                    gvars.dict_id_chat[id_device] = ""
                                gvars.emit("receive_chat_view_status", {
                                    "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                                return False
                            # time.sleep(1.0)
                            d.send_keys(f"{name}", clear=True)
                            gvars.eventlet.sleep(0.15)

                            try:
                                ck_ex = False
                                chat_list = d.xpath(
                                    '//*[@resource-id="com.zing.zalo:id/btn_search_result"]').all()

                                # if len(chat_num) > 0:
                                for item in chat_list:
                                    raw = item.text
                                    print("Raw là", raw)
                                    lines = [l for l in raw.split(
                                        "\n") if l.strip()]
                                    print(lines)
                                    if lines[0] == name:
                                        print("Có trùng khớp")
                                        item.click()
                                        ck_ex = True
                                        break
                                gvars.eventlet.sleep(1.0)
                                if not ck_ex:
                                    for id in range(len(list_prior_chat_boxes)):
                                        if list_prior_chat_boxes[id]['name'] == name:
                                            del list_prior_chat_boxes[id]
                                            data_update = {"num_phone_zalo": num_phone_zalo,
                                                           "list_prior_chat_boxes": list_prior_chat_boxes}
                                            update_base_document_json(
                                                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                            break

                                    for id in range(len(list_friend)):
                                        if list_friend[id]['name'] == name:
                                            del list_friend[id]
                                            data_update = {"num_phone_zalo": num_phone_zalo,
                                                           "list_friend": list_friend}
                                            update_base_document_json(
                                                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                                            break
                                    continue

                            except Exception:
                                gvars.emit("receive status", {
                                    "status": "Tài khoản không tồn tại"}, room=room)
                                gvars.dict_status_zalo[num_phone_zalo] = ""
                                del gvars.dict_queue_device[id_device][0]
                                if len(gvars.dict_queue_device[id_device]) == 0:
                                    gvars.dict_id_chat[id_device] = ""
                                print("Có lỗi à cậu")
                                return False

                            try:
                                btn = d(
                                    resourceId="com.zing.zalo:id/btn_send_message")
                                if btn.exists:
                                    btn.click()
                                    gvars.eventlet.sleep(1.0)
                                if d(textContains="Đóng").exists:
                                    d(textContains="Đóng").click()
                                    gvars.eventlet.sleep(0.5)
                            except Exception:
                                print("Lỗi có ở đây không")
                                pass
                    except Exception as e:
                        print(e)

                    check = False
                    check_seen = False
                    check_add_friend = False
                    if d(text="Đã gửi lời mời kết bạn").exists:
                        friend_or_not = "added"
                    else:
                        btn = d(
                            resourceId="com.zing.zalo:id/tv_function_privacy")
                        kb = d.xpath('//*[@text="Kết bạn"]')
                        if btn.exists or kb.exists:
                            print("chưa kết bạn")
                            friend_or_not = "no"
                        else:
                            friend_or_not = "yes"

                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                check_seen = True
                            list_prior_chat_boxes[id]['status'] = 'seen'
                            if 'friend_or_not' not in list_prior_chat_boxes[id].keys():
                                check_add_friend = True
                                list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                            else:
                                if list_prior_chat_boxes[id]['friend_or_not'] != friend_or_not:
                                    list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                                    check_add_friend = True
                            check = True
                            # check_add_friend = True
                            break

                    if not check:
                        list_prior_chat_boxes.append(
                            {"name": name, "phone": "", "time": "", "message": "", "status": "seen",  "friend_or_not": friend_or_not, "data_chat_box": ""})

                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'

                            break

                if type == 'image':

                    image_number -= 1

                    try:
                      # if id_device not in special_device:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        d.xpath(
                            '//*[@text="Tài liệu"]').click()
                        gvars.eventlet.sleep(1)

                        if d.xpath('//*[@text="Gần đây"]').exists:
                            d(description="Hiển thị gốc").click_exists(
                                timeout=3)
                            gvars.eventlet.sleep(0.2)
                            td = d.xpath(
                                '//*[@text="Tệp đã tải xuống"]')
                            if td.exists:
                                td.click()
                                gvars.eventlet.sleep(0.1)
                            else:
                                if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                    d(resourceId="android:id/title",
                                      text="Tệp đã tải xuống").click()
                                    # gvars.eventlet.sleep(0.1)
                                else:
                                    d.xpath(
                                        '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                            gvars.eventlet.sleep(0.1)
                        click_btn = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                        if click_btn.exists:
                            click_btn.click_exists(timeout=0.1)
                            gvars.eventlet.sleep(0.1)
                        btn1 = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                        btn2 = d(
                            resourceId="com.google.android.documentsui:id/item_root")
                        if btn1.exists:
                            btn1.click()
                            gvars.eventlet.sleep(0.1)
                        elif btn2.exists:
                            btn2.click()
                            gvars.eventlet.sleep(0.1)
                        if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                            # pass
                        else:
                            # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                            d.xpath(
                                '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                            gvars.eventlet.sleep(0.1)
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False
                elif type == 'file':

                    try:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        d.xpath(
                            '//*[@text="Tài liệu"]').click()
                        gvars.eventlet.sleep(1)

                        if d.xpath('//*[@text="Gần đây"]').exists:
                            d(description="Hiển thị gốc").click_exists(
                                timeout=3)
                            gvars.eventlet.sleep(0.2)
                            td = d.xpath(
                                '//*[@text="Tệp đã tải xuống"]')
                            if td.exists:
                                td.click()
                                gvars.eventlet.sleep(0.1)
                            else:
                                if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                    d(resourceId="android:id/title",
                                      text="Tệp đã tải xuống").click()
                                    # gvars.eventlet.sleep(0.1)
                                else:
                                    d.xpath(
                                        '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                            gvars.eventlet.sleep(0.1)
                        click_btn = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                        if click_btn.exists:
                            click_btn.click_exists(timeout=0.1)
                            gvars.eventlet.sleep(0.1)
                        btn1 = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                        btn2 = d(
                            resourceId="com.google.android.documentsui:id/item_root")
                        if btn1.exists:
                            btn1.click()
                        elif btn2.exists:
                            btn2.click()
                        if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                            # pass
                        else:
                            # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                            d.xpath(
                                '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                            gvars.eventlet.sleep(0.1)
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False

                elif type == 'text':

                    try:
                        d(resourceId="com.zing.zalo:id/chatinput_text").click()
                        gvars.eventlet.sleep(0.1)
                        d.send_keys(message, clear=True)
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False
                elif type == 'card':
                    try:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        gvars.eventlet.sleep(0.1)
                        d.xpath('//*[@text="Danh thiếp"]').click()
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/search_input_text").click()
                        gvars.eventlet.sleep(0.1)
                        d.send_keys(name_card, clear=True)
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/layoutcontact").click()
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/btn_done_add_item").click()
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        gvars.eventlet.sleep(0.1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)

                now = gvars.datetime.now()
                print("Ngày:", now.day)
                print("Tháng:", now.month)
                print("Năm:", now.year)
                print("Giờ:", now.hour)
                print("Phút:", now.minute)
                print("Giây:", now.second)
                hour = str(now.hour)
                minute = str(now.hour)
                if len(hour) == 1:
                    hour = f"0{hour}"
                if len(minute) == 1:
                    minute = f"0{minute}"
                time_str = f"{hour}:{minute} {now.day}/{now.month}/{now.year}"
                gvars.eventlet.sleep(1.0)
                gvars.join_room(room)
                check = False
                # pick = -1
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name:
                        check = True
                        if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                            list_prior_chat_boxes[id]['data_chat_box'] = ""
                        if type == 'text':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'])
                            data_chat_box.append(
                                {"you": [{'time': time_str, 'type': "text", "data": message}]})
                            list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'image':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'])
                            data_chat_box.append(
                                {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                            list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'file':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'])
                            data_chat_box.append(
                                {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                            list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'card':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'])
                            data_chat_box.append(
                                {"you": [{'time': time_str, 'type': "card", "data": f"{name_card}\nGọi điện\nNhắn tin", "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                            list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                                list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        break

                        # pick = id
                if not check:
                    data_chat_box = []
                    if type == 'text':
                        list_prior_chat_boxes.append(
                            {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": message, "status": "seen", "data_chat_box": ""})
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "text", "data": message}]})
                        list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'image':
                        list_prior_chat_boxes.append(
                            {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": f"image{image_number+1}.jpg", "status": "seen", "data_chat_box": ""})
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                        list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'file':
                        list_prior_chat_boxes.append(
                            {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": f"[File]\n{file_name}\n{file_size}", "status": "seen", "data_chat_box": ""})
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                        list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'card':
                        list_prior_chat_boxes.append(
                            {"name": name, "ava": ava, "phone": phone, "friend_or_not": friend_or_not, "time": time_str, "message": message, "status": "seen", "data_chat_box": ""})
                        data_chat_box = load_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'])
                        data_chat_box.append(
                            {"you": [{'time': time_str, 'type': "card", "data": message, "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                        list_prior_chat_boxes[-1]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[-1]['data_chat_box'], data_chat_box)
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))

                if extra_message != "":
                    try:
                        d(resourceId="com.zing.zalo:id/chatinput_text").click()
                        gvars.eventlet.sleep(0.1)
                        d.send_keys(extra_message, clear=True)
                        gvars.eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        gvars.dict_status_zalo[num_phone_zalo] = ""
                        del gvars.dict_queue_device[id_device][0]
                        if len(gvars.dict_queue_device[id_device]) == 0:
                            gvars.dict_id_chat[id_device] = ""
                        gvars.emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": extra_message}, room=room)
                        return False
                    now = gvars.datetime.now()
                    print("Ngày:", now.day)
                    print("Tháng:", now.month)
                    print("Năm:", now.year)
                    print("Giờ:", now.hour)
                    print("Phút:", now.minute)
                    print("Giây:", now.second)
                    hour = str(now.hour)
                    minute = str(now.hour)
                    if len(hour) == 1:
                        hour = f"0{hour}"
                    if len(minute) == 1:
                        minute = f"0{minute}"
                    time_str = f"{hour}:{minute} {now.day}/{now.month}/{now.year}"
                    gvars.eventlet.sleep(1.0)

                    id = 0
                    if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                        list_prior_chat_boxes[id]['data_chat_box'] = ""

                    list_prior_chat_boxes[id]['time'] = time_str
                    list_prior_chat_boxes[id]['message'] = extra_message
                    list_prior_chat_boxes[id]['status'] = "seen"
                    data_chat_box = load_data_chat_box_json(
                        list_prior_chat_boxes[id]['data_chat_box'])
                    data_chat_box.append(
                        {"you": [{'time': time_str, 'type': "text", "data": extra_message}]})
                    list_prior_chat_boxes[id]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[id]['data_chat_box'], data_chat_box)

            data_update = {"num_phone_zalo": num_phone_zalo,
                           "list_prior_chat_boxes": list_prior_chat_boxes}
            update_base_document_json(
                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
            if True:
                on_chat = False
                btn = d(resourceId="com.zing.zalo:id/action_bar_title")
                if btn.exists:
                    current_ntd = btn.get_text()

                    if current_ntd == name_share:
                        on_chat = True
                    else:
                        d.press("back")
                        if d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                            d.press("back")
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            d.press("back")
                if not on_chat:
                    items = d.xpath(
                        "//android.widget.FrameLayout[@text!='']").all()
                    check_ex = False
                    for item in items:
                        raw = item.text
                        lines = [l for l in raw.split(
                            "\n") if l.strip()]
                        if lines[0] == name_share:
                            item.click()
                            check_ex = True
                            break
                    if not check_ex:
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            if d.xpath('//*[@text="Zalo"]').exists:
                                try:
                                    d.xpath(
                                        '//*[@text="Zalo"]').click()
                                    gvars.eventlet.sleep(1.5)
                                except Exception:
                                    pass
                            else:
                                d.press("back")

                        try:
                            # d(text="Tìm kiếm").click()
                            d(text="Tìm kiếm").click()
                        except Exception as e:
                            print(e)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            gvars.emit("receive_chat_view_status", {
                                "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name_share}, room=room)
                            return False
                        # time.sleep(1.0)
                        d.send_keys(f"{name_share}", clear=True)
                        gvars.eventlet.sleep(0.15)

                        try:
                            chat_list = d.xpath(
                                '//*[@resource-id="com.zing.zalo:id/btn_search_result"]').all()

                            # if len(chat_num) > 0:
                            for item in chat_list:
                                raw = item.text
                                print("Raw là", raw)
                                lines = [l for l in raw.split(
                                    "\n") if l.strip()]
                                if lines[0] == name_share:
                                    print("Có trùng khớp")
                                    item.click()
                                    break
                            gvars.eventlet.sleep(1.0)
                            # print("Nhấn được chat  chưa")
                        except Exception as e:
                            gvars.emit("receive status", {
                                "status": "Tài khoản không tồn tại"}, room=room)
                            gvars.dict_status_zalo[num_phone_zalo] = ""
                            del gvars.dict_queue_device[id_device][0]
                            if len(gvars.dict_queue_device[id_device]) == 0:
                                gvars.dict_id_chat[id_device] = ""
                            # print("Có lỗi à cậu")
                            print("Lỗi gặp phải là: ", e)
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                gvars.eventlet.sleep(1.0)
                        except Exception as e:
                            print("Lỗi gặp phải là: ", e)
                            pass

            gvars.emit("receive_share_status", {
                "status": "Đã chia sẻ tin nhắn thành công"}, room=room)
            gvars.emit('receive_list_prior_chat_box', {
                'user_name': name_share, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, room=room)
        except Exception as e:
            print(e)

            gvars.dict_status_zalo[num_phone_zalo] = ""
            gvars.dict_status_update_pvp[num_phone_zalo] = 2
            del gvars.dict_queue_device[id_device][0]
            if len(gvars.dict_queue_device[id_device]) == 0:
                gvars.dict_id_chat[id_device] = ""
            handle_chat_view(d, num_phone_zalo)
            return False
        num_message += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = gvars.json.load(f)

        for id in range(len(device_status['max_message_per_day'])):
            if num_phone_zalo in device_status['max_message_per_day'][id].keys():
                device_status['max_message_per_day'][id][num_phone_zalo] -= 1
                if extra_message != "":
                    device_status['max_message_per_day'][id][num_phone_zalo] -= 1
        gvars.dict_status_zalo[num_phone_zalo] = ""
        gvars.dict_status_update_pvp[num_phone_zalo] = 2
        del gvars.dict_queue_device[id_device][0]
        if len(gvars.dict_queue_device[id_device]) == 0:
            gvars.dict_id_chat[id_device] = ""
        # two = time.time()
        # print(two-one)
        handle_chat_view(d, num_phone_zalo)

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            gvars.json.dump(device_status, f, indent=4)
