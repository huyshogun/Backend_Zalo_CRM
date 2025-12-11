
import zalo_crm_global_variables as gvars
from zalo_crm_other_functions import switch_account, dump_data_chat_box_json
from zalo_crm_crawl_functions import api_get_list_friend, api_get_list_group, api_get_list_invite_friend, api_update_list_prior_chat_boxes, api_update_data_one_chat_box, api_update_list_mems_one_group, api_update_data_1vs1_chat_box, api_update_data_gr_chat_box, api_update_list_unseen_chat_boxes
from zalo_crm_crud_database import already_sent_number, read_sent_number, log_sent_number, already_sent_phone_zalo, log_sent_phone_zalo, update_base_document_json, get_base_id_zalo_json


def background_first_crawl_per_day(id_device):

    file_path = f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json"
    # global device_connect
    # global gvars.dict_devices
    # print("Id của máy là ", id_device)
    try:
        d = gvars.u2.connect(id_device)
        # d.app_start('com.zing.zalo', stop=True)
        print("Id của máy là ", id_device)
        gvars.device_connect[id_device] = True
        # gvars.dict_devices.append(id_device)
    except Exception as e:
        print(e)
        print("Thiết bị đã ngắt kết nối", id_device)
        gvars.eventlet.sleep(5)
        gvars.device_connect[id_device] = False
        background_first_crawl_per_day(id_device)
        return True

    print("Bắt đầu cào dữ liệu và lấy dữ liệu người dùng ", id_device)
    max_mes = []
    max_add = []
    if gvars.os.path.exists(file_path):
        gvars.os.remove(file_path)  # Xóa file nếu có

    device_status = {
        "active": True,
        "max_message_per_day": max_mes,
        "max_add_friend_per_day": max_add,
        "update": False
    }

    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json", 'w') as f:
        gvars.json.dump(device_status, f, indent=4)

    file_path_new = f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json"
    if gvars.os.path.exists(file_path_new):
        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json', 'r', encoding='utf-8') as f:
            zalo_data = gvars.json.load(f)
        for i in range(len(zalo_data)):
            zalo_data[i]['status'] = False
    else:
        zalo_data = []

    name_zalos = []
    try:
        # if True:
        # Lấy danh sách tên các tài khoản zalo hiện có
        d.app_start("com.zing.zalo", stop=True)
        gvars.eventlet.sleep(1.0)
        d(resourceId="com.zing.zalo:id/maintab_metab").click()
        gvars.eventlet.sleep(1.0)
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[2]').click()

        gvars.eventlet.sleep(1.5)
        d.swipe_ext(gvars.u2.Direction.FORWARD)
        gvars.eventlet.sleep(1.0)
        try:
            d(resourceId="com.zing.zalo:id/itemSwitchAccount").click()
        except Exception as e:
            background_first_crawl_per_day(id_device)
            return True
        gvars.eventlet.sleep(1.0)

        # items = d.xpath("//android.widget.TextView[@text!='']").all()
        nope = ['Đã đăng nhập',
                "Chuyển tài khoản", "Thêm tài khoản để đăng nhập nhanh.", "Thêm tài khoản"]
        elements = d(resourceId="com.zing.zalo:id/name")

        for elem in elements:
            name_zalo_1 = elem.info.get('text', '').strip()
            if name_zalo_1 not in nope:
                # print("Có tồn tại thêm tài khoản không ", name_zalo_1)
                name_zalos.append(name_zalo_1)

        print(name_zalos)

        for id in range(len(name_zalos)):
            if "Thêm tài khoản" in name_zalos[id] or name_zalos[id] == "Thêm tài khoản":
                del name_zalos[id]
                break

        for id in range(len(name_zalos)):
            if name_zalos[id] == "Thêm tài khoản":
                continue

            for it in range(len(zalo_data)):
                if zalo_data[it]['name'] == name_zalos[id] and zalo_data[it]['num_phone_zalo'] != "":
                    zalo_data[it]['status'] = True

            d.app_start("com.zing.zalo", stop=True)
            gvars.eventlet.sleep(1)
            d(resourceId="com.zing.zalo:id/maintab_metab").click()
            gvars.eventlet.sleep(1.5)
            if d(resourceId="com.zing.zalo:id/subtitle_list_me_tab").exists:
                d(resourceId="com.zing.zalo:id/subtitle_list_me_tab").click()
            else:
                d(resourceId="com.zing.zalo:id/heading_list_setting_container").click()
            gvars.eventlet.sleep(1.5)
            avatar_b64 = ""
            try:
                iv = d(resourceId="com.zing.zalo:id/rounded_avatar_frame")
                img = iv.screenshot()

                # 2. Giảm độ phân giải ảnh nhỏ hơn, vẫn giữ aspect ratio
                max_w, max_h = 200, 200
                # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                img.thumbnail((max_w, max_h), resample=gvars.Image.BILINEAR)

                # 3. Nén ảnh với JPEG (chất lượng vừa phải kèm optimize) để có kích thước tối ưu
                buf = gvars.io.BytesIO()
                # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                img.save(buf, format="JPEG", optimize=True, quality=75)

                # 4. Encode sang gvars.base64 (chuỗi ASCII ngắn và nhẹ hơn)
                # gvars.base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
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

            except Exception as e:
                pass
            # zalo_data[id]['ava'] = avatar_b64
            gvars.eventlet.sleep(1.0)
            d.xpath(
                '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[2]').click()
            gvars.eventlet.sleep(1.0)
            d(resourceId="com.zing.zalo:id/setting_text_primary",
              text="Thông tin").click()
            gvars.eventlet.sleep(1.5)
            num_phone_zalo = d(
                resourceId="com.zing.zalo:id/tv_phone_number").get_text()
            print("Số điện thoại là: ", num_phone_zalo)
            num_phone_zalo = num_phone_zalo.replace(" ", "")
            num_phone_zalo = num_phone_zalo.replace("+84", "0")
            if not already_sent_phone_zalo(num_phone_zalo):
                log_sent_phone_zalo(num_phone_zalo)
                gvars.dict_new_friend[num_phone_zalo] = {}

            ck_zalo = False
            for it in range(len(zalo_data)):
                if zalo_data[it]['num_phone_zalo'] == num_phone_zalo:
                    zalo_data[it]['name'] = name_zalos[id]
                    zalo_data[it]['ava'] = avatar_b64
                    zalo_data[it]['status'] = True
                    list_prior_chat_boxes = zalo_data[it]['list_prior_chat_boxes']
                    list_group = zalo_data[it]['list_group']
                    if "has_first_update" not in zalo_data[it].keys():
                        zalo_data[it]['has_first_update'] = False
                    ck_zalo = True
                    break
            if not ck_zalo:
                for it in range(len(zalo_data)):
                    if zalo_data[it]['name'] == name_zalos[id] and zalo_data[it]['num_phone_zalo'] != "":
                        zalo_data[it]['num_phone_zalo'] = num_phone_zalo
                        zalo_data[it]['ava'] = avatar_b64
                        zalo_data[it]['status'] = True
                        list_prior_chat_boxes = zalo_data[it]['list_prior_chat_boxes']
                        list_group = zalo_data[it]['list_group']
                        if "has_first_update" not in zalo_data[it].keys():
                            zalo_data[it]['has_first_update'] = False
                        ck_zalo = True
                        break
            if not ck_zalo:
                # for it in range(len(zalo_data)):
                #    if zalo_data[it]['name'] == name_zalos[id] and zalo_data[it]['num_phone_zalo'] != "":
                zalo_data.append({"id_device": id_device, "num_phone_zalo": num_phone_zalo, "name": name_zalos[id], "ava": avatar_b64, "list_friend": [
                ], "list_group": [], "list_invite_friend": [], "list_prior_chat_boxes": [], "list_unseen_chat_boxes": [], "status": True, "has_first_update": False})
                list_prior_chat_boxes = []
                list_group = []
            # zalo_data[id]['num_phone_zalo'] = num_phone_zalo
            gvars.dict_device_and_phone[id_device].append(num_phone_zalo)
            gvars.dict_status_zalo[num_phone_zalo] = ""
            gvars.dict_status_update_pvp[num_phone_zalo] = 0
            gvars.dict_phone_device[num_phone_zalo] = id_device
            with open(f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json", 'w', encoding="utf-8") as f:
                gvars.json.dump(zalo_data, f, ensure_ascii=False, indent=4)
            gvars.eventlet.sleep(5.0)

            tag_name = {}
            data_chat_boxes = {}
            friend_or_nots = {}
            list_mems = {}
            check_mems = {}

            for chat in list_prior_chat_boxes:
                if 'tag' in chat.keys():
                    if chat['tag'] != "":
                        tag_name[chat['name']] = chat['tag']
                if "data_chat_box" in chat.keys():
                    if chat["data_chat_box"] == []:
                        chat["data_chat_box"] = ""
                        data_chat_boxes[chat['name']] = chat["data_chat_box"]
                    
                    if isinstance(chat["data_chat_box"], list):
                        chat["data_chat_box"] = dump_data_chat_box_json(chat["data_chat_box"], chat["data_chat_box"])

                    if chat["data_chat_box"]:
                        print("Đoạn chat này khác rỗng ", chat['name'])
                        data_chat_boxes[chat['name']] = chat["data_chat_box"]
                if 'friend_or_not' in chat.keys():
                    if chat['friend_or_not'] != "":
                        friend_or_nots[chat['name']] = chat['friend_or_not']
            
            for group in list_group:
                if 'list_mems' in group.keys():
                    list_mems[group['name']] = group['list_mems']
                if 'check_mems' in group.keys():
                    check_mems[group['name']] = group['check_mems']
                    
        # phone = [zalo['num_phone_zalo'] for zalo in zalo_data if zalo['num_phone_zalo'] != ""]
        # for num_phone_zalo in phone:

            try:
                print("Bắt đầu lấy danh sách bạn bè")
                has_first_update = False
                pick = -1
                for it in range(len(zalo_data)):
                    if zalo_data[it]['num_phone_zalo'] == num_phone_zalo:
                        list_friend = zalo_data[it]['list_friend']
                        if 'list_prior_chat_boxes' in zalo_data[it].keys():
                            old_list_prior_chat_boxes = zalo_data[it]['list_prior_chat_boxes']
                        else:
                            old_list_prior_chat_boxes = []
                        has_first_update = zalo_data[it]['has_first_update']
                        # has_first_update = has_first_update
                        zalo_data[it]['ava'] = avatar_b64
                        zalo_data[it]['status'] = True
                        ck_zalo = True
                        pick = it
                        break
                result1, update_again = api_get_list_friend(
                    {"num_phone_zalo": num_phone_zalo}, has_first_update)

                while update_again:
                    # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                    gvars.eventlet.sleep(2.0)
                    result1, update_again = api_get_list_friend(
                        {"num_phone_zalo": num_phone_zalo}, has_first_update)
                    # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]

                if not has_first_update:
                    print("Bắt đầu lấy danh sách nhóm")
                    result2, update_again = api_get_list_group(
                        {"num_phone_zalo": num_phone_zalo}, list_mems, check_mems)
                    while update_again:
                        # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                        # background_first_crawl_per_day(id_device)
                        # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                        gvars.eventlet.sleep(2.0)
                        result2, update_again = api_get_list_group(
                            {"num_phone_zalo": num_phone_zalo}, list_mems, check_mems)
                        # return True   

                    print("Bắt đầu lấy danh sách gửi kết bạn")
                    result3, update_again = api_get_list_invite_friend(
                        {"num_phone_zalo": num_phone_zalo})

                    while update_again:
                        # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                        # background_first_crawl_per_day(id_device)
                        # return True
                        gvars.eventlet.sleep(2.0)
                        result3, update_again = api_get_list_invite_friend(
                            {"num_phone_zalo": num_phone_zalo})

                print("Bắt đầu lấy danh sách chat ưu tiến")
                result4, update_again = api_update_list_prior_chat_boxes(
                    {"num_phone_zalo": num_phone_zalo}, tag_name=tag_name, data_chat_boxes=data_chat_boxes, friend_or_nots=friend_or_nots, max_chat_boxes=2000, scroll_or_not=True)
                while update_again:
                    # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                    gvars.eventlet.sleep(2.0)
                    result4, update_again = api_update_list_prior_chat_boxes(
                        {"num_phone_zalo": num_phone_zalo}, tag_name=tag_name, data_chat_boxes=data_chat_boxes)
                    # return True

                print("Bắt đầu lấy danh sách chat chưa đọc")
                result5, update_again = api_update_list_unseen_chat_boxes({"num_phone_zalo":  num_phone_zalo})
                while update_again:
                    # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                    gvars.eventlet.sleep(2.0)
                    result5, update_again = api_update_list_unseen_chat_boxes(
                        {"num_phone_zalo": num_phone_zalo})
                    
                if has_first_update and len(result4) > 0 and len(old_list_prior_chat_boxes) > 0:
                    try:
                        to_remove = {(old.get('name'), old.get('message'))
                                     for old in old_list_prior_chat_boxes}
                        result4 = [new for new in result4 if (
                            new.get('name'), new.get('message')) not in to_remove]
                    except Exception as e:
                        print(e)

                result4 = [r['name'] for r in result4]

                print("Bắt đầu lấy lịch sử chat")
                try:
                    for name_ntd in result4:
                        # if name_ntd not in result2:
                        try:
                            gr_or_pvp = "pvp"
                            if name_ntd in result2:
                                gr_or_pvp = "gr"
                            result6 = api_update_data_one_chat_box(
                                {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, gr_or_pvp=gr_or_pvp, update=True)
                            while not gvars.device_connect[id_device]:
                                # gvars.dict_devices = [
                                #    dv for dv in gvars.dict_devices if dv != id_device]
                                # background_first_crawl_per_day(id_device)
                                gvars.eventlet.sleep(2.0)
                                print("Đang chờ thiết bị kết nối lại ", id_device)
                                # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                                # return True
                        except Exception as e:
                            result6 = api_update_data_one_chat_box(
                                {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, gr_or_pvp=gr_or_pvp, update=True)

                except Exception as e:
                    print(e)

                if not has_first_update:

                    for name_ntd in result2:
                        try:
                            result7 = api_update_list_mems_one_group(
                                {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, update=True)
                            while not gvars.device_connect[id_device]:
                                # gvars.dict_devices = [
                                #    dv for dv in gvars.dict_devices if dv != id_device]
                                # background_first_crawl_per_day(id_device)
                                gvars.eventlet.sleep(2.0)
                                print("Đang chờ thiết bị kết nối lại ", id_device)
                                # gvars.dict_devices = [dv for dv in gvars.dict_devices if dv != id_device]
                                # return True
                        except Exception as e:
                            result7 = api_update_list_mems_one_group(
                                {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, update=True)

                # if not has_first_update:
                    zalo_data[pick]['has_first_update'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json", 'w', encoding="utf-8") as f:
                        gvars.json.dump(
                            zalo_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print("Đã gặp lỗi trong quá trình lấy thông tin zalo ", e)

            if id < len(name_zalos)-1:
                try:
                    d = switch_account(d, name_zalos[id+1])
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            if current_phone != "":
                                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                                    "num_phone_zalo": current_phone, "status": False})
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                        "num_phone_zalo": num_phone_zalo, "status": False})
                    with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json', 'r', encoding='utf-8') as f:
                        zalo_data = gvars.json.load(f)
                except Exception as e:
                    print("Đã gặp lỗi trong quá trình đổi tài khoản zalo ", e)

    except Exception as e:
        print("Đã gặp lỗi trong quá trình lấy thông tin zalo ", e)
        gvars.eventlet.sleep(5)
        background_first_crawl_per_day(id_device)
        return True

    print("Cào dữ liệu thành công ", id_device)
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json', 'r') as f:
        device_status = gvars.json.load(f)
    d.app_start("com.zing.zalo", stop=True)
    gvars.eventlet.sleep(2.0)
    device_status['active'] = False
    device_status['update'] = True

    for phone in gvars.dict_device_and_phone[id_device]:
        device_status['max_message_per_day'].append({phone: 300})
        device_status['max_add_friend_per_day'].append({phone: 5})

    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json", 'w') as f:
        gvars.json.dump(device_status, f, indent=4)
    # gvars.dict_devices.append(id_device)
    print("Tiến trình bắt đầu ", id_device)
    # gvars.dict_devices.append(id_device)
    # return [result1, result2, result3, result4, result5, result6]
    return True


def background_update_data_loop(id_device):

    while True:
        try:

            try:
                update_d = gvars.u2.connect(id_device)
                # global device_connect
                gvars.device_connect[id_device] = True
            except Exception as e:
                print("Thiết bị đã ngắt kết nối", id_device)
                gvars.device_connect[id_device] = False
                continue

            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json', 'r') as f:
                    device_status = gvars.json.load(f)
                if not device_status['update']:
                    print("Dữ liệu chưa update xong ", id_device)
                    gvars.eventlet.sleep(2)
                    continue
            except Exception as e:
                print(f"Dữ liệu chưa update xong {id_device} ", e)
                gvars.eventlet.sleep(2)
                continue

            if gvars.now_phone_zalo[id_device] == "":
                print("Đang không có số điện thoại nào gọi đến, id là ", id_device)
                gvars.eventlet.sleep(2)
                continue

            print(
                f"Số điện thoại hiện tại của {id_device} là: ", gvars.now_phone_zalo[id_device])
            try:
                document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                    "num_phone_zalo": gvars.now_phone_zalo[id_device]})[0]
            except Exception as e:
                print(e)
                continue

            # id_device = document['id_device']

            try:
                documents = get_base_id_zalo_json(
                    "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{id_device}", {"id_device": id_device})
            except Exception as e:
                print(e)
                continue

            current_phone = ""
            for it in documents:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    if current_phone != "" and current_phone != gvars.now_phone_zalo[id_device]:
                        gvars.now_phone_zalo[id_device] = current_phone
                        document = it
                    break

            list_group = document['list_group']
            list_prior_chat_boxes = document['list_prior_chat_boxes']
            if len(list_group) > 0:
                name_group = [group['name'] for group in list_group]
            else:
                name_group = []

            # docs giờ là một list chứa mọi document tìm được
            # id_device = document['id_device']
            user_name = document['name']
            # list_prior_chat_boxes = document['list_prior_chat_boxes']
            curr_phone_zalo = gvars.now_phone_zalo[id_device]
            if gvars.dict_status_zalo[curr_phone_zalo] != "":
                print("Có tiến trình đang chạy ",
                    gvars.dict_status_zalo[curr_phone_zalo])
                gvars.eventlet.sleep(1)
                continue

            while True:
                if gvars.dict_status_zalo[curr_phone_zalo] != "":
                    print("Có tiến trình đang chạy ",
                        gvars.dict_status_zalo[curr_phone_zalo])
                    break
                if curr_phone_zalo != gvars.now_phone_zalo[id_device]:
                    print("Số điện thoại đã bị thay đổi: ",
                        gvars.now_phone_zalo[id_device])
                    break
                print("Trạng thái hiện tại là: ",
                    gvars.dict_status_zalo[curr_phone_zalo])
                btn = update_d(resourceId="com.zing.zalo:id/action_bar_title")

                if btn.exists:

                    try:
                        # chỗ này cần bỏ đi vì tốn tài nguyên
                        name_ntd = btn.get_text()
                        if update_d(text="Đã gửi lời mời kết bạn").exists:
                            friend_or_not = "added"
                        else:
                            btn = update_d(
                                resourceId="com.zing.zalo:id/tv_function_privacy")
                            kb = update_d.xpath('//*[@text="Kết bạn"]')
                            if btn.exists or kb.exists:
                                friend_or_not = "no"
                            else:
                                friend_or_not = "yes"

                        if 'list_prior_chat_boxes' not in document.keys():
                            document['list_prior_chat_boxes'] = []
                        list_prior_chat_boxes = document['list_prior_chat_boxes']

                        elems = update_d.xpath(
                            '//*[@content-desc and contains(@content-desc, "Thông báo của Zalo")]').all()
                        for el in elems:
                            print("Có tồn tại phần tử thông báo ",
                                el.info.get("contentDescription"))

                        if len(elems) > 0:
                            ck_noti = False
                            for elem in elems:
                                # if elem.exists:
                                desc_value = elem.info.get("contentDescription")
                                print(desc_value)
                                new_name_ntd = desc_value.replace(
                                    "Thông báo của Zalo:", "")
                                if ":" in new_name_ntd:
                                    new_name_ntd = new_name_ntd.split(':')[0]
                                new_name_ntd = new_name_ntd.strip()
                                data_ntd = new_name_ntd
                                # print(data_ntd)
                                print("Tên cuộc thông báo mới là: ", new_name_ntd)
                                check = False
                                pick = -1
                                for id in range(len(list_prior_chat_boxes)):
                                    if list_prior_chat_boxes[id]['name'] == data_ntd:
                                        pick = id
                                        check = True
                                        break
                                if not check:
                                    list_prior_chat_boxes.append(
                                        {"name": data_ntd, "time": "", "message": "", "status": "unseen", "data_chat_box": ""})
                                # print("Đã đọc chưa nhỉ:",
                                #      list_prior_chat_boxes[pick]['status'])
                                if list_prior_chat_boxes[pick]['status'] == "seen":
                                    list_prior_chat_boxes[pick]['status'] = "unseen"
                                    list_prior_chat_boxes.insert(
                                        0, list_prior_chat_boxes.pop(pick))
                                    data_update = {"num_phone_zalo": curr_phone_zalo,
                                                "list_prior_chat_boxes": list_prior_chat_boxes}
                                    ck_noti = True
                            if ck_noti:
                                # print("Đã gửi socket chưa")
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", data_update)
                                gvars.socketio.emit('receive_list_prior_chat_box', {
                                    'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})

                        try:
                            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json', 'r') as f:
                                device_status = gvars.json.load(f)
                        except Exception as e:
                            print("Có lỗi xảy ra", e)
                            break

                        if device_status['active']:
                            # print("Có active không")
                            if name_ntd in name_group:
                                # if True:
                                try:
                                    print("Tên nhóm là: ", name_ntd)
                                    if curr_phone_zalo != gvars.now_phone_zalo[id_device]:
                                        print(
                                            "Số điện thoại hiện tại đã bị thay đổi: ", gvars.now_phone_zalo[id_device])
                                        break
                                    chat_box_on_chat = api_update_data_gr_chat_box(
                                        update_d, {"num_phone_zalo": curr_phone_zalo, "name_ntd": name_ntd}, document)
                                    print("Dữ liễu đoạn chat là:",
                                        chat_box_on_chat)
                                except Exception as e:
                                    print("Có lỗi khi cào tin nhắn nhóm: ", e)
                                    gvars.dict_status_zalo[curr_phone_zalo] = ""
                                    chat_box_on_chat = False
                                if not chat_box_on_chat:
                                    break
                                if chat_box_on_chat and len(chat_box_on_chat) > 0:
                                    document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                                        "num_phone_zalo": curr_phone_zalo})[0]
                                    list_prior_chat_boxes = document['list_prior_chat_boxes']

                                    gvars.socketio.emit('receive_new_message_from_ntd', {
                                        'name_ntd': name_ntd, 'friend_or_not': friend_or_not, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                                    gvars.socketio.emit('receive_list_prior_chat_box', {
                                        'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                            else:
                                document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                                    "num_phone_zalo": curr_phone_zalo})[0]
                                if curr_phone_zalo != gvars.now_phone_zalo[id_device]:
                                    print(
                                        "Số điện thoại hiện tại đã bị thay đổi: ", gvars.now_phone_zalo[id_device])
                                    break
                                try:
                                    chat_box_on_chat = api_update_data_1vs1_chat_box(
                                        update_d, {"num_phone_zalo": curr_phone_zalo, "name_ntd": name_ntd}, document)
                                except Exception as e:
                                    print("Có lỗi khi lấy tin nhắn 1vs1", e)
                                    gvars.dict_status_zalo[curr_phone_zalo] = ""
                                    chat_box_on_chat = False
                                if not chat_box_on_chat:
                                    break
                                if chat_box_on_chat and len(chat_box_on_chat) > 0:
                                    document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                                        "num_phone_zalo": curr_phone_zalo})[0]
                                    list_prior_chat_boxes = document['list_prior_chat_boxes']
                                    # print("Lịch sử box chat được thêm vào là:",
                                    #    chat_box_on_chat)
                                    gvars.socketio.emit('receive_new_message_from_ntd', {
                                        'name_ntd': name_ntd, 'friend_or_not': friend_or_not, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                                    gvars.socketio.emit('receive_list_prior_chat_box', {
                                        'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                    except Exception as e:
                        gvars.dict_status_zalo[curr_phone_zalo] = ""
                        print("Lỗi gặp phải là ", e)
                        break

                else:
                    break
                gvars.eventlet.sleep(3)
            try:
                ut = update_d.xpath('//*[@text="Ưu tiên"]')
            except Exception as e:
                continue

            if ut.exists:
                if curr_phone_zalo != gvars.now_phone_zalo[id_device]:
                    print("Số điện thoại đã bị thay đổi: ",
                        gvars.now_phone_zalo[id_device])
                    continue
                print("Có tồn tại ưu tiên")
                ck_noti = False
                boxes = api_update_list_prior_chat_boxes(
                    {"num_phone_zalo": curr_phone_zalo}, max_chat_boxes=8, scroll_or_not=False)

                if not boxes or len(boxes) == 0:
                    gvars.eventlet.sleep(3)
                    continue
                num = len(boxes)-1
                if num == -1:
                    continue
                # print(boxes)
                for ik in range(len(boxes)):
                    it = num-ik
                    for id in range(len(list_prior_chat_boxes)):
                        if boxes[it]['name'] == list_prior_chat_boxes[id]['name']:
                            if ":" in boxes[it]['message']:
                                boxes[it]['message'] = boxes[it]['message'].split(":")[
                                    1].strip()
                            if "…" in boxes[it]['message']:
                                boxes[it]['message'] = boxes[it]['message'].split("…")[
                                    0].strip()

                            if boxes[it]['message'] not in list_prior_chat_boxes[id]['message'] and list_prior_chat_boxes[id]['message'] not in boxes[it]['message']:
                                print("Tin nhắn 1 là: ", boxes[it]['message'])
                                print("Tin nhắn 2 là: ",
                                    list_prior_chat_boxes[id]['message'])
                                list_prior_chat_boxes[id]['time'] = boxes[it]['time']
                                list_prior_chat_boxes[id]['message'] = boxes[it]['message']
                                list_prior_chat_boxes[id]['status'] = "unseen"
                                list_prior_chat_boxes.insert(
                                    0, list_prior_chat_boxes.pop(id))
                                data_update = {"num_phone_zalo": curr_phone_zalo,
                                            "list_prior_chat_boxes": list_prior_chat_boxes}
                                ck_noti = True

                            break
                if ck_noti:
                    print("Có gọi socket phiên bản 2 không")
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", data_update)
                    gvars.socketio.emit('receive_list_prior_chat_box', {
                        'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
        except Exception as e:
            print("Lỗi trong quá trình lắng nghe tin nhắn ", e)

        gvars.eventlet.sleep(2)
