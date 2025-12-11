import zalo_crm_global_variables as gvars
from zalo_crm_crud_database import already_sent_number, read_sent_number, log_sent_number, update_base_document_json, get_base_id_zalo_json
from zalo_crm_other_functions import safe_click, safe_normal_click, load_data_chat_box_json, dump_data_chat_box_json


def get_list_friends_u2(d: gvars.u2.Device, id_device="", max_friends: int = 150, scroll_delay: float = 1.0, retire=3, has_update=False, friend_name=[], num_phone_zalo="", list_friend_old=[]):
    """
    Lấy toàn bộ bạn bè từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_friends: giới hạn tối đa số bạn bè thu thập
    """
    friends = list_friend_old
    seen = set()
    previous_last = ""
    same_count = 0

    d.app_start("com.zing.zalo", stop=True)
    gvars.eventlet.sleep(1.0)
    # d.implicitly_wait(3.0)

    try:
        d(resourceId="com.zing.zalo:id/maintab_contact").click()
        gvars.eventlet.sleep(1.0)
    except Exception as e:
        if retire > 0:
            get_list_friends_u2(d, retire=retire-1)
        else:
            return False
    try:
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/layoutTab"]/android.widget.FrameLayout[1]').click()
        gvars.eventlet.sleep(1.0)
    except Exception:
        pass

    try:
        if has_update:
            if d(resourceId="com.zing.zalo:id/header_page_new_friend").exists:
                d(resourceId="com.zing.zalo:id/header_page_new_friend").click()
            else:
                return friends
            gvars.eventlet.sleep(1.0)
    except Exception as e:
        pass

        # 2) Lặp scroll & thu thập
    while len(friends) < max_friends:
        # 2.1 lấy tất cả item bạn bè đang hiển thị
        items = d.xpath(
            "//android.widget.FrameLayout"
            "[@resource-id='com.zing.zalo:id/cel_contact_tab_contact_cell']"
        ).all()

        num_item = len(items)
        for id in range(num_item):
            raw = items[id].text or ""
            name = raw.split("\n", 1)[0].strip()
            if not name or name in seen or name in friend_name or "Tài khoản" in name or "Zalo" in raw:
                continue

            seen.add(name)
            try:

                items[id].click()
                gvars.eventlet.sleep(1.0)

                try:
                    btn = d(
                        resourceId="com.zing.zalo:id/btn_send_message")
                    if btn.exists:
                        btn.click()
                        gvars.eventlet.sleep(0.5)
                except Exception:
                    pass

                if d(textContains="Đóng").exists:
                    d(textContains="Đóng").click()
                    gvars.eventlet.sleep(0.5)
                d(resourceId="com.zing.zalo:id/action_bar_title").click()
                gvars.eventlet.sleep(1.0)
                avatar_b64 = ""
                try:
                    iv = d(resourceId="com.zing.zalo:id/rounded_avatar_frame")
                    '''
                    img = iv.screenshot()  # trả về PIL.Image
                    buf = gvars.io.BytesIO()
                    img.save(buf, format="PNG")
                    avatar_b64 = gvars.base64.b64encode(buf.getvalue()).decode("ascii")
                    '''
                    img = iv.screenshot()
                    max_w, max_h = 200, 200
                    img.thumbnail((max_w, max_h),
                                    resample=gvars.Image.BILINEAR)
                    buf = gvars.io.BytesIO()
                    img.save(buf, format="JPEG", optimize=True, quality=75)
                    avatar_b64 = gvars.base64.b64encode(
                        buf.getvalue()).decode("ascii")
                    if not already_sent_number(gvars.AVA_NUMBER_PATH):
                        ava_number = 0
                    else:
                        ava_number = read_sent_number(
                            gvars.AVA_NUMBER_PATH)
                    with open(f"{gvars.IMAGE_FILE_DATA_PATH}/ava_{ava_number}.txt", "w", encoding="utf-8") as f:
                        f.write(avatar_b64)

                    log_sent_number(ava_number+1, gvars.AVA_NUMBER_PATH)

                    avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/ava_{ava_number}.txt"
                except Exception as e:
                    print("Lỗi gặp phải là ", e)

                bd = ""
                d.xpath(
                    '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[3]').click()
                gvars.eventlet.sleep(0.5)
                d(resourceId="com.zing.zalo:id/setting_text_primary",
                    text="Thông tin").click()
                gvars.eventlet.sleep(0.5)
                try:
                    dob = d(resourceId="com.zing.zalo:id/tv_dob")
                    bd = dob.get_text()
                    gvars.eventlet.sleep(0.5)
                except Exception as e:
                    print("Không lấy được ngày tháng năm sinh ", name)
                d.press('back')
                gvars.eventlet.sleep(0.5)
                d.press('back')
                gvars.eventlet.sleep(0.5)

                friends.append({
                    "name": name,
                    "ava": avatar_b64,
                    "day_of_birth": bd
                })

                data_update = {"list_friend": friends,
                                "num_phone_zalo": num_phone_zalo}
                update_base_document_json(
                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

                d.press('back')
                gvars.eventlet.sleep(1.0)

                d.press('back')
                gvars.eventlet.sleep(1.0)

            except Exception as e:
                print("Lỗi trong quá trình lấy danh sách bạn bè", e)
                while not d(resourceId="com.zing.zalo:id/maintab_contact").exists:
                    d.press('back')
                    gvars.eventlet.sleep(1.0)

            if id < num_item - 1:
                items = d.xpath(
                    "//*[@resource-id='com.zing.zalo:id/cel_contact_tab_contact_cell']").all()

        if len(friends) >= max_friends:
            break

        # Kiểm tra có còn dữ liệu mới không
        if items:
            last_raw = items[-1].text or ""
            if last_raw == previous_last:
                same_count += 1
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw

        # 2.2 scroll lên để load thêm
        w, h = d.window_size()
        d.swipe(w//2, int(h*0.8), w//2, int(h*0.2), duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return friends


def get_list_groups_u2(d: gvars.u2.Device, list_mems={}, check_mems={}, max_groups: int = 50, scroll_delay: float = 1.0, retire=3):
    """
    Lấy toàn bộ nhóm từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_groups: giới hạn tối đa số nhóm thu thập
    """
    groups = []
    seen = set()
    previous_last = ""
    same_count = 0
    d.app_start("com.zing.zalo", stop=True)
    # d.implicitly_wait(3.0)

    # 1) Chuyển sang tab Danh bạ
    try:
        d(resourceId="com.zing.zalo:id/maintab_contact").click()
        gvars.eventlet.sleep(1.0)
    except Exception as e:
        if retire > 0:
            get_list_groups_u2(d, retire=retire-1)
        else:
            return False

    # 2) Chuyển sang phần Nhóm
    try:
        d(resourceId="com.zing.zalo:id/tv_groups").click()
        gvars.eventlet.sleep(1)
    except Exception as e:
        if retire > 0:
            get_list_groups_u2(d, retire=retire-1)
        else:
            return False

    # 3) Lặp scroll & thu thập
    while len(groups) < max_groups:
        # lấy tất cả item nhóm đang hiển thị
        items = d.xpath(
            "//android.widget.FrameLayout"
            "[@resource-id='com.zing.zalo:id/cel_contact_tab_group_cell']"
        ).all()
        if len(items) == 0:
            break

        for it in items:
            raw = it.text or ""
            # Tách thành các dòng không rỗng
            lines = [line.strip() for line in raw.split("\n") if line.strip()]
            name = lines[0] if len(lines) > 0 else ""
            time_str = lines[1] if len(lines) > 1 else ""
            message = "\n".join(lines[2:]) if len(lines) > 2 else ""

            if not name or name in seen:
                continue

            seen.add(name)
            if name in list_mems.keys():
                list_mem = list_mems[name]
            else:
                list_mem = []

            if name in check_mems.keys():
                check_mem = check_mems[name]
            else:
                check_mem = True
            groups.append({
                "name": name,
                "time": time_str,
                "message": message,
                "list_mems": list_mem,
                "check_mems": check_mem
                # "avatar": (nếu cần, thêm screenshot của ImageView con tương tự)
            })
            if len(groups) >= max_groups:
                break

        if len(groups) >= max_groups:
            break

        # Kiểm tra còn nội dung mới
        if items:
            last_raw = items[-1].text or ""
            if last_raw == previous_last:
                same_count += 1
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw

        # Scroll lên để load thêm
        w, h = d.window_size()
        d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.2), duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return groups


def get_list_invite_friends_u2(d: gvars.u2.Device, max_friends: int = 100, scroll_delay: float = 1.0, retire=3):
    """
    Lấy toàn bộ bạn bè chưa kết bạn (invite) từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_friends: giới hạn tối đa số bạn bè thu thập
    """
    d.app_start("com.zing.zalo", stop=True)
    # d.implicitly_wait(3.0)

    invite_friends = []
    seen = set()
    previous_last = ""
    same_count = 0

    # 1) Chuyển sang tab Danh bạ
    try:
        d(resourceId="com.zing.zalo:id/maintab_contact").click()
        gvars.eventlet.sleep(1.0)
    except Exception as e:
        if retire > 0:
            get_list_invite_friends_u2(d, retire=retire-1)
        else:
            return False
    try:
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/layoutTab"]/android.widget.FrameLayout[1]').click()
        gvars.eventlet.sleep(1.0)
    except Exception:
        pass
    try:
        d(resourceId="com.zing.zalo:id/suggest_friend_request").click()
        gvars.eventlet.sleep(1.0)
        try:
            d.xpath("//android.widget.TextView[@text='XEM THÊM']").click()
            gvars.eventlet.sleep(1.0)
        except Exception as e:
            pass
    except Exception as e:
        if retire > 0:
            get_list_invite_friends_u2(d, retire=retire-1)
        else:
            return False
    # 2) Lặp scroll & thu thập
    while len(invite_friends) < max_friends:
        # 2.1 Lấy tất cả ô contact invite
        items = d.xpath(
            "//*[@resource-id='com.zing.zalo:id/info_contact_row']").all()
        id = 1

        if len(items) == 0:
            break

        # start=1 để khớp với indexing 1-based của XPath
        for idx, it in enumerate(items, start=1):
            # Sáu xử lý lấy text theo từng field
            try:
                name_el = d.xpath(
                    f"//*[@resource-id='com.zing.zalo:id/info_contact_row'][{idx}]"
                    f"//*[@resource-id='com.zing.zalo:id/name']"
                )
                name_text = name_el.text
            except Exception:
                name_text = ""
            if name_text in seen or name_text == "":
                continue
            try:
                inv_el = d.xpath(
                    f"//*[@resource-id='com.zing.zalo:id/info_contact_row'][{idx}]"
                    f"//*[@resource-id='com.zing.zalo:id/tvInvitation']"
                )
                inv_text = inv_el.get().text
            except Exception:
                inv_text = ""

            try:
                detail_el = d.xpath(
                    f"//*[@resource-id='com.zing.zalo:id/info_contact_row'][{idx}]"
                    f"//*[@resource-id='com.zing.zalo:id/tvInvitationDetail']"
                )
                detail_text = detail_el.get().text

            except Exception:
                detail_text = ""

            try:
                ivm = d.xpath(
                    f"//*[@resource-id='com.zing.zalo:id/info_contact_row'][{idx}]"
                    f"//*[@resource-id='com.zing.zalo:id/buddy_dp']"
                )

                iv = ivm.get()
                img = iv.screenshot()
                max_w, max_h = 200, 200
                img.thumbnail((max_w, max_h), resample=gvars.Image.BILINEAR)
                buf = gvars.io.BytesIO()
                img.save(buf, format="JPEG", optimize=True, quality=75)
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
            except Exception:
                avatar_b64 = ""

    # Loại trùng tên nếu cần
            seen.add(name_text)

            invite_friends.append({
                "name": name_text,
                "ava": avatar_b64,
                "message_invite": inv_text,
                "message_detail": detail_text
            })

        if len(invite_friends) >= max_friends:
            break

        if len(invite_friends) == 0:
            break

        # Kiểm tra có nội dung mới không
        if items:
            id = len(items)
            while True:
                try:
                    last_raw = d.xpath(
                        f"//*[@resource-id='com.zing.zalo:id/info_contact_row'][{id}]"
                        f"//*[@resource-id='com.zing.zalo:id/name']"
                    ).get()
                    break
                except Exception:
                    id = id - 1

            if last_raw.text == previous_last:
                same_count += 1
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw.text

        # 2.2 Swipe để load thêm
        w, h = d.window_size()
        d.swipe(w//2, int(h*0.8), w//2, int(h*0.2), duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return invite_friends


def get_list_prior_chat_boxes_u2(d: gvars.u2.Device, tag_name={}, data_chat_boxes={}, friend_or_nots={}, max_chat_boxes: int = 1500, scroll_delay: float = 1.0, retire=3, scroll_or_not=True):
    """
    Lấy toàn bộ nhóm từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_groups: giới hạn tối đa số nhóm thu thập
    """
    chat_boxes = []
    seen = set()
    previous_last = ""
    same_count = 0
    # clm = d.xpath('//*[@text="Ưu tiên"]')
    d.app_start("com.zing.zalo", stop=True)
    # d.implicitly_wait(3.0)
    # Phần khởi động

    # 3) Lặp scroll & thu thập
    while len(chat_boxes) < max_chat_boxes:
        # lấy tất cả item nhóm đang hiển thị
        '''
        if d(text="Xem thêm").exists:
            d(text="Xem thêm").click()
            gvars.eventlet.sleep(1.0)
        '''
        items = d.xpath("//android.widget.FrameLayout[@text!='']").all()

        for it in items:
            raw = it.text or ""
            if "Media Box" in raw or "Zalo" in raw or "Tin nhắn từ người lạ" in raw or "ngừng hoạt động" in raw or "vào nhóm và cộng đồng" in raw or "Kết bạn" in raw:
                continue
            if "Xem thêm" in raw:
                it.click()
                gvars.eventlet.sleep(1.0)
                if d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                    d.press('back')
                    gvars.eventlet.sleep(1.0)
                break
            print(raw)
            # Tách thành các dòng không rỗng
            lines = [line.strip()
                        for line in raw.split("\n") if line.strip()]
            name = lines[0] if len(lines) > 0 else ""
            time_str = lines[1] if len(lines) > 1 else ""
            message = "\n".join(lines[2:]) if len(lines) > 2 else ""

            if not name or name in seen:
                continue
            now = gvars.datetime.now()
            temp = time_str.replace(" ", "")
            if "phút" in time_str:
                time_str = time_str.replace("phút", "")
                time_str = time_str.replace(" ", "")
                dt_minus_48 = now - gvars.timedelta(minutes=int(time_str))
                hour = dt_minus_48.hour
                minute = dt_minus_48.minute
                day = dt_minus_48.day
                month = dt_minus_48.month
                year = dt_minus_48.year
                if len(str(hour)) == 1:
                    hour = f"0{hour}"
                if len(str(minute)) == 1:
                    minute = f"0{minute}"
                if len(str(day)) == 1:
                    day = f"0{day}"
                if len(str(month)) == 1:
                    month = f"0{month}"
                time_str = f"{hour}:{minute} {day}/{month}/{year}"
            elif "giờ" in time_str:
                dt_minus_4h = now - gvars.timedelta(hours=4)
                hour = dt_minus_4h.hour
                minute = dt_minus_4h.minute
                day = dt_minus_4h.day
                month = dt_minus_4h.month
                year = dt_minus_4h.year
                if len(str(hour)) == 1:
                    hour = f"0{hour}"
                if len(str(minute)) == 1:
                    minute = f"0{minute}"
                if len(str(day)) == 1:
                    day = f"0{day}"
                if len(str(month)) == 1:
                    month = f"0{month}"
                time_str = f"{hour}:{minute} {day}/{month}/{year}"
            elif "T" in time_str or "CN" in time_str:
                today = gvars.date.today()
                time_str = time_str.replace(" ", "")
                target = gvars.mapping.get(time_str.upper())
                if target is None:
                    raise ValueError("Không xác định được thứ từ đầu vào.")
                offset = (today.weekday() - target) % 7
                result = today - gvars.timedelta(days=offset)
                day = result.day
                month = result.month
                year = result.year
                if len(str(day)) == 1:
                    day = f"0{day}"
                if len(str(month)) == 1:
                    month = f"0{month}"
                print("Ngày của", time_str.upper(),
                        "gần nhất:", result.strftime("%d/%m/%Y"))
                time_str = f"{day}/{month}/{year}"
            elif len(temp) <= 6:
                today = gvars.date.today()
                year = today.year
                time_str += "/" + str(year)

            seen.add(name)
            if name in tag_name.keys():
                tag = tag_name[name]
            else:
                tag = ""

            if name in data_chat_boxes.keys():
                print("Đoạn chat này tồn tại lần 2 ", name)
                data_chat_box = data_chat_boxes[name]
            else:
                data_chat_box = ""
                
            if name in friend_or_nots.keys():
                friend_or_not = friend_or_nots[name]
                chat_boxes.append({
                    "name": name,
                    "ava": "",
                    "time": time_str,
                    "message": message,
                    "status": "seen",
                    "tag": tag,
                    "data_chat_box": data_chat_box,
                    "friend_or_not": friend_or_not
                    # "avatar": (nếu cần, thêm screenshot của ImageView con tương tự)
                })
            else:
                chat_boxes.append({
                    "name": name,
                    "ava": "",
                    "time": time_str,
                    "message": message,
                    "status": "seen",
                    "tag": tag,
                    "data_chat_box": data_chat_box
                    # "avatar": (nếu cần, thêm screenshot của ImageView con tương tự)
                })
            if len(chat_boxes) >= max_chat_boxes:
                break

        if len(chat_boxes) >= max_chat_boxes:
            break

        # Kiểm tra còn nội dung mới
        if items:
            last_raw = items[-1].text or ""
            if last_raw == previous_last:
                same_count += 1
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw
        if not scroll_or_not:
            break
        # Scroll lên để load thêm
        w, h = d.window_size()
        d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.2), duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return chat_boxes


def get_list_unseen_chat_boxes_u2(d: gvars.u2.Device, max_chat_boxes: int = 50, scroll_delay: float = 1.0, retire=3):
    """
    Lấy toàn bộ nhóm từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_groups: giới hạn tối đa số nhóm thu thập
    """
    chat_boxes = []
    seen = set()
    previous_last = ""
    same_count = 0
    d.app_start("com.zing.zalo", stop=True)
    # d.implicitly_wait(3.0)
    # Phần khởi động

    gvars.eventlet.sleep(1.0)
    d.xpath('//*[@resource-id="com.zing.zalo:id/tab_container_right"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[1]').click()
    gvars.eventlet.sleep(1.0)
    d.xpath(
        '//*[@resource-id="com.zing.zalo:id/rv_popover_options"]/android.widget.LinearLayout[1]').click()
    gvars.eventlet.sleep(1.0)
    # 3) Lặp scroll & thu thập
    while len(chat_boxes) < max_chat_boxes:
        # lấy tất cả item nhóm đang hiển thị
        items = d.xpath("//android.widget.FrameLayout[@text!='']").all()

        if len(items) == 0:
            break

        for it in items:
            raw = it.text or ""
            if "Media Box" in raw or "Zalo" in raw or "Tin nhắn từ người lạ" in raw:
                continue
            print(raw)
            # Tách thành các dòng không rỗng
            lines = [line.strip()
                        for line in raw.split("\n") if line.strip()]
            name = lines[0] if len(lines) > 0 else ""
            time_str = lines[1] if len(lines) > 1 else ""
            message = "\n".join(lines[2:]) if len(lines) > 2 else ""

            if not name or name in seen:
                continue
            now = gvars.datetime.now()
            temp = time_str.replace(" ", "")
            if "phút" in time_str:
                time_str = time_str.replace("phút", "")
                time_str = time_str.replace(" ", "")
                dt_minus_48 = now - gvars.timedelta(minutes=int(time_str))
                hour = dt_minus_48.hour
                minute = dt_minus_48.minute
                day = dt_minus_48.day
                month = dt_minus_48.month
                year = dt_minus_48.year
                time_str = f"{hour}:{minute} {day}/{month}/{year}"
            elif "giờ" in time_str:
                dt_minus_4h = now - gvars.timedelta(hours=4)
                hour = dt_minus_4h.hour
                minute = dt_minus_4h.minute
                day = dt_minus_4h.day
                month = dt_minus_4h.month
                year = dt_minus_4h.year
                time_str = f"{hour}:{minute} {day}/{month}/{year}"
            elif "T" in time_str or "CN" in time_str:
                today = gvars.date.today()
                time_str = time_str.replace(" ", "")
                target = gvars.mapping.get(time_str.upper())
                if target is None:
                    raise ValueError("Không xác định được thứ từ đầu vào.")
                offset = (today.weekday() - target) % 7
                result = today - gvars.timedelta(days=offset)
                day = result.day
                month = result.month
                year = result.year
                print("Ngày của", time_str.upper(),
                        "gần nhất:", result.strftime("%d/%m/%Y"))
                time_str = f"{day}/{month}/{year}"
            elif len(temp) <= 6:
                today = gvars.date.today()
                year = today.year
                time_str += "/" + str(year)

            seen.add(name)
            chat_boxes.append({
                "name": name,
                "time": time_str,
                "message": message,
                "status": "unseen",
                "tag": ""
                # "avatar": (nếu cần, thêm screenshot của ImageView con tương tự)
            })
            if len(chat_boxes) >= max_chat_boxes:
                break

        if len(chat_boxes) >= max_chat_boxes:
            break

        # Kiểm tra còn nội dung mới
        if items:
            last_raw = items[-1].text or ""
            if last_raw == previous_last:
                same_count += 1
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw

        # Scroll lên để load thêm
        w, h = d.window_size()
        d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.2), duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return chat_boxes


def get_data_chat_boxes_u2(d: gvars.u2.Device, gr_or_pvp: str, time_and_mes, max_scroll: int = 20, scroll_delay: float = 1.0):
    """
    Trả về dict chứa hộp chat hiện có trong màn hình chat của Zalo Android.
    - div_child_selector: dict để tìm tab/conversation (ví dụ {'resourceId': '...', 'text': 'Tên bạn'})
    - device_url: đường dẫn để kết nối uiautomator2 (ví dụ '192.168.1.100:5555')
    - max_scroll: số lần swipe để load tin cũ.
    - scroll_delay: thời gian chờ giữa các lần swipe.
    """
    # d = run_start(d)
    data_chat_box = []
    chat = {}
    seen = set()
    previous_last = None
    same_count = 0
    check_you_or_fr = 0
    check_call = 0
    lack = False
    chat_lack_raw = []
    chat_lack = []
    nope = ["[Hình ảnh]", "[Sticker]", "[Vị trí]", "[Video]"]

    if gr_or_pvp == "pvp":
        try:
            fr = d(resourceId="com.zing.zalo:id/action_bar_title").get_text()
            name_sender = fr
        except Exception as e:
            print("Đã gặp lỗi trong quá trình lấy lịch sử tin nhắn ", e)
            return data_chat_box
    check = True
    for nm in range(max_scroll + 1):
        # 2) Tìm tất cả message bubble
        try:
            items = d.xpath("//android.view.ViewGroup[@text!='']").all()
            num = len(items) - 1
            # Đọc từ dưới lên trên (các tin mới trước)
            for id in range(num+1):
                raw = items[num-id].text or ""

                if gr_or_pvp == 'gr':
                    if raw in seen and not any(it in raw for it in nope) and raw not in chat_lack_raw:
                        continue

                else:
                    if raw in seen:
                        continue

                if "Tin nhắn đã được thu hồi" in raw:
                    continue

                print(time_and_mes)
                print(raw)
                check_1 = True
                if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                    bounds = items[num-id].info['bounds']
                    width, height = bounds['right'] - \
                        bounds['left'], bounds['bottom'] - bounds['top']
                    # if height <= 400:
                    #    continue
                formatted = gvars.date.today().strftime("%d/%m/%Y")
                raw = raw.replace("Hôm nay", formatted)
                if "[File]" in raw:
                    raw = raw.split('…')[0]
                    if time_and_mes['message'] != "":
                        if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                            check = False
                            check_1 = False
                            break
                    mes = time_and_mes['message'].split("\n")
                    if len(mes) > 1:
                        if mes[1] in raw:
                            check = False
                            check_1 = False
                            break
                seen.add(raw)
                lines = [l for l in raw.split("\n") if l.strip()]

                if time_and_mes['message'] in lines:
                    if "[Hình ảnh]" not in time_and_mes['message']:
                        check = False
                        check_1 = False
                        break
                    else:
                        if time_and_mes['time'] in lines or time_and_mes['time'] == "":
                            check = False
                            check_1 = False
                            break
                if "Gọi điện" in raw or "Nhắn tin" in raw:
                    check = False
                    check_1 = False

                if not check_1:
                    break

                # Loại bỏ dòng 'Đã nhận'
                if lines and "Đã nhận" in lines[-1]:
                    lines = lines[:-1]
                    check_you_or_fr = 1
                if lines and "Đã gửi" in lines[-1]:
                    lines = lines[:-1]
                    check_you_or_fr = 1
                if lines and "Đã xem" in lines[-1]:
                    lines = lines[:-1]
                    check_you_or_fr = 1

                # Xử lý file/image
                if lines and "[File]" in raw:
                    # time_str = lines[-1] if len(lines) > 1 else ''
                    def has_time_token(s):
                        return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                    if has_time_token(lines[0]) and has_time_token(lines[-1]):
                        time_str = lines[-1]
                        message = '\n'.join(lines[1:-1])

                        if check_you_or_fr == 1:
                            data_chat_box.append(chat)
                            chat = {}

                        if check_you_or_fr == 2:
                            data_chat_box.append(chat)
                            chat = {}

                        if gr_or_pvp == 'gr':
                            if len(lines) < 4 or "[Hình ảnh]" in lines[1]:
                                if raw not in chat_lack_raw:
                                    lack = True
                                    chat_lack_raw.append(raw)
                            else:
                                name_sender = lines[1]
                                message = '\n'.join(lines[2:-1])
                        check_you_or_fr = 0

                    elif has_time_token(lines[0]):
                        time_str = lines[0]
                        message = '\n'.join(lines[1:])
                        # name_sender = lines[1]
                        if check_you_or_fr == 1:
                            data_chat_box.append(chat)
                            chat = {}

                        if check_you_or_fr == 2:
                            data_chat_box.append(chat)
                            chat = {}

                        if gr_or_pvp == 'gr':
                            if len(lines) < 3 or "[Hình ảnh]" in lines[1]:
                                if raw not in chat_lack_raw:
                                    lack = True
                                    chat_lack_raw.append(raw)
                            else:
                                name_sender = lines[1]
                                message = '\n'.join(lines[2:])
                        check_you_or_fr = 0

                    elif has_time_token(lines[-1]):
                        time_str = lines[-1]
                        message = '\n'.join(lines[:-1])

                        if check_you_or_fr == 1:
                            data_chat_box.append(chat)
                            chat = {}

                        if check_you_or_fr == 2:
                            data_chat_box.append(chat)
                            chat = {}

                        if gr_or_pvp == 'gr':
                            if len(lines) < 3 or "[Hình ảnh]" in lines[0]:
                                if raw not in chat_lack_raw:
                                    lack = True
                                    chat_lack_raw.append(raw)
                            else:
                                name_sender = lines[0]
                                message = '\n'.join(lines[1:-1])
                        check_you_or_fr = 0
                    else:
                        time_str = ""
                        if gr_or_pvp == 'gr':
                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            cx = bounds['left'] + int(width * 0.075)
                            cy = bounds['top'] + int(width * 0.075)
                            d = safe_normal_click(d, cx, cy)
                            gvars.eventlet.sleep(1.0)
                            btn = d.xpath('//*[@text="Xem trang cá nhân"]')
                            if btn.exists:
                                print("Đây là người nhắn")
                                if raw in chat_lack_raw:
                                    if len(chat_lack) > 0:
                                        del chat_lack[-1]
                                    if len(chat_lack_raw) > 0:
                                        del chat_lack_raw[-1]
                                check_you_or_fr = 2
                                name_sender = lines[0]
                                if not lack:
                                    chat[f'{name_sender}'] = []
                                message = '\n'.join(lines[1:])
                                '''
                                bounds = btn.info['bounds']
                                width, height = bounds['right'] - \
                                    bounds['left'], bounds['bottom'] - \
                                    bounds['top']
                                cx = bounds['left'] + int(width * 0.075)
                                cy = bounds['top'] + int(width * 0.075)
                                '''
                                d.press('back')
                                gvars.eventlet.sleep(1.0)
                                items = d.xpath(
                                    "//android.view.ViewGroup[@text!='']").all()
                            else:
                                message = '\n'.join(lines)
                                if raw not in chat_lack_raw:
                                    lack = True
                                    chat_lack_raw.append(raw)
                        else:
                            message = '\n'.join(lines)
                    '''
                    now = gvars.datetime.now()
                    print("Ngày:", now.day)
                    print("Tháng:", now.month)
                    print("Năm:", now.year)
                    print("Giờ:", now.hour)
                    print("Phút:", now.minute)
                    print("Giây:", now.second)
                    message = f"{message} {now.hour}:{now.minute}:{now.second} {now.day}/{now.month}/{now.year}"
                    '''
                    numm = message.split("\n")
                    if len(numm) > 2:
                        message = "\n".join(numm[:2])

                    formatted = gvars.date.today().strftime("%d/%m/%Y")
                    time_str = time_str.replace("Hôm nay", formatted)
                    typ = 'image' if any(
                        ext in message for ext in ('jpg', 'png')) else 'file'

                    if check_you_or_fr == 0:
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        cx = bounds['left'] + int(width * 0.24)
                        cy = bounds['top'] + height * 0.5
                        print(f"Toa độ click là {cx}, {cy}")
                        # d.long_click(cx, cy, duration=1.0)
                        d = safe_click(d, cx, cy)
                        gvars.eventlet.sleep(1.5)
                        btn = d.xpath('//*[@text="Trả lời"]')
                        if btn.exists:
                            print("Có tồn tại Trả lời")
                            th = d.xpath('//*[@text="Thu hồi"]')
                            if not th.exists:
                                check_you_or_fr = 2
                                if not lack:
                                    chat[f'{name_sender}'] = []
                            else:
                                print("Có tồn tại Thu hồi")
                                check_you_or_fr = 1
                                chat['you'] = []

                            d.press('back')
                            gvars.eventlet.sleep(1.0)
                            items = d.xpath(
                                "//android.view.ViewGroup[@text!='']").all()

                        else:
                            print("Không tồn tại Trả lời")
                            check_you_or_fr = 1
                            chat['you'] = []
                            # continue

                    if check_you_or_fr == 1:
                        if typ == 'image':
                            '''
                            img = iv.screenshot()  # trả về PIL.Image
                            buf = gvars.io.BytesIO()
                            img.save(buf, format="PNG")
                            avatar_b64 = gvars.base64.b64encode(buf.getvalue()).decode("ascii")
                            '''
                            iv = items[num-id].screenshot()
                            img = iv.convert("RGB") if hasattr(
                                iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))

                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']

                            left = bounds['left'] + int(width * 0.225)
                            right = bounds['left'] + int(width * 0.95)
                        # top = bounds['top']
                            top = 0
                        # bottom = bounds['bottom'] - int(height * 0.08)
                            bottom = int(height * 0.92)

                            cropped = img.crop((left, top, right, bottom))

                            cropped_small = cropped.filter(
                                gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                            buf = gvars.io.BytesIO()
                            cropped_small.save(buf, format="PNG")

                            # output_path = "cropped_output.jpg"
                            # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                            avatar_b64 = gvars.base64.b64encode(
                                buf.getvalue()).decode("ascii")

                            if not already_sent_number(gvars.MES_NUMBER_PATH):
                                mes_number = 0
                            else:
                                mes_number = read_sent_number(
                                    gvars.MES_NUMBER_PATH)
                            with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                f.write(avatar_b64)

                            log_sent_number(
                                mes_number+1, gvars.MES_NUMBER_PATH)

                            avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            chat['you'].append(
                                {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                        else:
                            chat['you'].append(
                                {"time": time_str, "type": typ, "data": message})
                    else:
                        if typ == 'image':
                            iv = items[num-id].screenshot()
                            img = iv.convert("RGB") if hasattr(
                                iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))

                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']

                            left = bounds['left'] + int(width * 0.125)
                            right = bounds['left'] + int(width * 0.85)
                        # top = bounds['top']
                            top = 0
                        # bottom = bounds['bottom'] - int(height * 0.08)
                            bottom = int(height * 0.92)

                            cropped = img.crop((left, top, right, bottom))

                            cropped_small = cropped.filter(
                                gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                            buf = gvars.io.BytesIO()
                            cropped_small.save(buf, format="PNG")

                            # output_path = "cropped_output.jpg"
                            # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                            avatar_b64 = gvars.base64.b64encode(
                                buf.getvalue()).decode("ascii")

                            if not already_sent_number(gvars.MES_NUMBER_PATH):
                                mes_number = 0
                            else:
                                mes_number = read_sent_number(
                                    gvars.MES_NUMBER_PATH)
                            with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                f.write(avatar_b64)

                            log_sent_number(
                                mes_number+1, gvars.MES_NUMBER_PATH)

                            avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            if gr_or_pvp == 'pvp':
                                chat[f'{name_sender}'].append(
                                    {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                            else:
                                if lack:
                                    chat_lack.append(
                                        {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                                    lack = False
                                elif not lack and len(chat_lack) > 0:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                                        chat[f'{name_sender}'] = chat_lack + \
                                            chat[f'{name_sender}']
                                        chat_lack = []
                                        chat_lack_raw = []
                                else:
                                    chat[f'{name_sender}'].append(
                                        {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                        else:
                            if gr_or_pvp == 'pvp':
                                chat[f'{name_sender}'].append(
                                    {"time": time_str, "type": typ, "data": message, "file_data": ""})
                            else:
                                if lack:
                                    chat_lack.append(
                                        {"time": time_str, "type": typ, "data": message, "file_data": ""})
                                    lack = False
                                elif not lack and len(chat_lack) > 0:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": typ, "data": message, "file_data": ""})
                                        chat[f'{name_sender}'] = chat_lack + \
                                            chat[f'{name_sender}']
                                        chat_lack = []
                                        chat_lack_raw = []
                                else:
                                    chat[f'{name_sender}'].append(
                                        {"time": time_str, "type": typ, "data": message, "file_data": ""})

                else:
                    # Xác định time và message
                    time_str = ''
                    message = ''
                    if lines:
                        # kiểm tra dấu giờ phút
                        def has_time_token(s):
                            return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                        if has_time_token(lines[0]) and has_time_token(lines[-1]):
                            time_str = lines[-1]
                            message = '\n'.join(lines[1:-1])

                            if check_you_or_fr == 1:
                                data_chat_box.append(chat)
                                chat = {}

                            if check_you_or_fr == 2:
                                data_chat_box.append(chat)
                                chat = {}

                            if gr_or_pvp == 'gr':
                                if "[Hình ảnh]" in lines[1] or "[Vị trí]" in lines[1] or "[Sticker]" in lines[1]:
                                    if raw not in chat_lack_raw:
                                        lack = True
                                        chat_lack_raw.append(raw)
                                elif len(lines) < 4:
                                    message = "[Video]"
                                    name_sender = lines[1]
                                else:
                                    name_sender = lines[1]
                                    message = '\n'.join(lines[2:-1])

                            check_you_or_fr = 0

                        elif has_time_token(lines[0]):
                            time_str = lines[0]
                            message = '\n'.join(lines[1:])
                            if check_you_or_fr == 1:
                                data_chat_box.append(chat)
                                chat = {}

                            if check_you_or_fr == 2:
                                data_chat_box.append(chat)
                                chat = {}

                            if gr_or_pvp == 'gr':
                                if "[Hình ảnh]" in lines[1] or "[Vị trí]" in lines[1] or "[Sticker]" in lines[1]:
                                    if raw not in chat_lack_raw:
                                        lack = True
                                        chat_lack_raw.append(raw)
                                elif len(lines) < 3:
                                    message = "[Video]"
                                    name_sender = lines[1]
                                else:
                                    name_sender = lines[1]
                                    message = '\n'.join(lines[2:])

                            check_you_or_fr = 0

                        elif has_time_token(lines[-1]):
                            time_str = lines[-1]
                            message = '\n'.join(lines[:-1])
                            if check_you_or_fr == 1:
                                data_chat_box.append(chat)
                                chat = {}
                            if check_you_or_fr == 2:
                                data_chat_box.append(chat)
                                chat = {}

                            check_you_or_fr = 0

                            if gr_or_pvp == 'gr':
                                if "[Hình ảnh]" in lines[0] or "[Vị trí]" in lines[0] or "[Sticker]" in lines[0]:
                                    if raw not in chat_lack_raw:
                                        lack = True
                                        chat_lack_raw.append(raw)
                                else:
                                    bounds = items[num-id].info['bounds']
                                    width, height = bounds['right'] - \
                                        bounds['left'], bounds['bottom'] - \
                                        bounds['top']
                                    cx = bounds['left'] + int(width * 0.075)
                                    cy = bounds['top'] + int(width * 0.075)
                                    d = safe_normal_click(d, cx, cy)
                                    gvars.eventlet.sleep(1.0)
                                    btn = d(text="Xem trang cá nhân")
                                    if btn.exists:
                                        print("Đây là người nhắn")
                                        if raw in chat_lack_raw:
                                            if len(chat_lack) > 0:
                                                del chat_lack[-1]
                                            if len(chat_lack_raw) > 0:
                                                del chat_lack_raw[-1]
                                        check_you_or_fr = 2
                                        if len(lines) < 3:
                                            message = "[Video]"
                                            name_sender = lines[0]
                                        else:
                                            name_sender = lines[0]
                                            message = '\n'.join(lines[1:-1])
                                        if not lack:
                                            chat[f'{name_sender}'] = []
                                        d.press('back')
                                        gvars.eventlet.sleep(1.0)
                                        items = d.xpath(
                                            "//android.view.ViewGroup[@text!='']").all()
                                    else:
                                        print("Không có người nhắn")
                                        message = '\n'.join(lines[:-1])
                                        if raw not in chat_lack_raw:
                                            lack = True
                                            chat_lack_raw.append(raw)

                        else:
                            time_str = ""
                            if gr_or_pvp == 'gr':
                                bounds = items[num-id].info['bounds']
                                width, height = bounds['right'] - \
                                    bounds['left'], bounds['bottom'] - \
                                    bounds['top']
                                cx = bounds['left'] + int(width * 0.075)
                                cy = bounds['top'] + int(width * 0.075)
                                d = safe_normal_click(d, cx, cy)
                                gvars.eventlet.sleep(1.0)
                                btn = d.xpath('//*[@text="Xem trang cá nhân"]')
                                if btn.exists:
                                    print("Đây là người nhắn")
                                    if raw in chat_lack_raw:
                                        if len(chat_lack) > 0:
                                            del chat_lack[-1]
                                        if len(chat_lack_raw) > 0:
                                            del chat_lack_raw[-1]
                                    check_you_or_fr = 2
                                    name_sender = lines[0]
                                    if not lack:
                                        chat[f'{name_sender}'] = []
                                    message = '\n'.join(lines[1:])
                                    d.press('back')
                                    gvars.eventlet.sleep(1.0)
                                    items = d.xpath(
                                        "//android.view.ViewGroup[@text!='']").all()
                                else:
                                    message = '\n'.join(lines)
                                    if raw not in chat_lack_raw:
                                        lack = True
                                        chat_lack_raw.append(raw)
                            else:
                                message = '\n'.join(lines)

                        formatted = gvars.date.today().strftime("%d/%m/%Y")
                        time_str = time_str.replace("Hôm nay", formatted)
                        if check_you_or_fr == 0 and "Cuộc gọi thoại đi" not in message and "Cuộc gọi thoại đến" not in message and "Tin nhắn đã được thu hồi" not in message:
                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            cx = bounds['left'] + int(width * 0.24)
                            cy = bounds['top'] + height * 0.5
                            print("Đã click rồi")
                            # d.long_click(cx, cy, duration=1.0)
                            d = safe_click(d, cx, cy)
                            print(f"Tọa độ là {cx}, {cy}")
                            gvars.eventlet.sleep(1.5)
                            btn = d.xpath('//*[@text="Trả lời"]')
                            if btn.exists:
                                info = btn.info

                                print("Có tồn tại Trả lời")
                                th = d.xpath('//*[@text="Thu hồi"]')
                                if not th.exists:
                                    check_you_or_fr = 2
                                    if not lack:
                                        chat[f'{name_sender}'] = []
                                else:
                                    print("Có tồn tại Thu hồi")
                                    check_you_or_fr = 1
                                    chat['you'] = []

                                d.press('back')
                                gvars.eventlet.sleep(1.0)
                                items = d.xpath(
                                    "//android.view.ViewGroup[@text!='']").all()

                            else:
                                print("Không tồn tại Trả lời")
                                check_you_or_fr = 1
                                chat['you'] = []
                                # items = d.xpath("//android.view.ViewGroup[@text!='']").all()
                    # Phân loại
                    '''
                    if lines and "[Sticker]" in message:
                        if check_you_or_fr == 1:
                        chat[f'you_{id_y}'].append({"time": time_str, "type": "sticker", "data": message})
                        else:
                        chat[f'{sender}_{id_f}'].append({"time": time_str, "type": "sticker", "data": message})
                    '''
                    if "Tin nhắn đã được thu hồi" in message:
                        pass
                    elif "[Hình ảnh]" in message or "[Sticker]" in message or "[Video]" in message:
                        if check_you_or_fr == 1:
                            if "[Sticker]" in message:
                                left_rate = 0.65
                                right_rate = 0.95
                                top_rate = 0.05
                                bottom_rate = 0.95
                            else:
                                left_rate = 0.225
                                right_rate = 0.95
                                top_rate = 0
                                bottom_rate = 0.92

                            if "[Video]" not in message:
                                iv = items[num-id].screenshot()
                                img = iv.convert("RGB") if hasattr(
                                    iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))
                                bounds = items[num-id].info['bounds']
                                width, height = bounds['right'] - \
                                    bounds['left'], bounds['bottom'] - \
                                    bounds['top']
                                left = bounds['left'] + int(width * left_rate)
                                right = bounds['left'] + \
                                    int(width * right_rate)
                            # top = bounds['top']
                                top = 0 + int(height * top_rate)
                            # bottom = bounds['bottom'] - int(height * 0.08)
                                bottom = 0 + int(height * bottom_rate)
                                cropped = img.crop((left, top, right, bottom))
                                cropped_small = cropped.filter(
                                    gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                                buf = gvars.io.BytesIO()
                                cropped_small.save(buf, format="PNG")
                            # output_path = "cropped_output.jpg"
                            # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                                avatar_b64 = gvars.base64.b64encode(
                                    buf.getvalue()).decode("ascii")

                                if not already_sent_number(gvars.MES_NUMBER_PATH):
                                    mes_number = 0
                                else:
                                    mes_number = read_sent_number(
                                        gvars.MES_NUMBER_PATH)
                                with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                    f.write(avatar_b64)

                                log_sent_number(
                                    mes_number+1, gvars.MES_NUMBER_PATH)

                                avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            else:
                                avatar_b64 = ""
                                try:
                                    iv = d(resourceId="com.zing.zalo:id/video_view")
                                    img = iv.screenshot()
                                    # max_w, max_h = 200, 200
                                    # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                                    cropped_small = img

                                    buf = gvars.io.BytesIO()
                                    cropped_small.save(buf, format="PNG")
                                    # gvars.base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                                    avatar_b64 = gvars.base64.b64encode(
                                        buf.getvalue()).decode("ascii")
                                except Exception as e:
                                    print("Có lỗi trong quá trình lấy dữ liệu video ", e)

                                if not already_sent_number(gvars.MES_NUMBER_PATH):
                                    mes_number = 0
                                else:
                                    mes_number = read_sent_number(
                                        gvars.MES_NUMBER_PATH)
                                with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                    f.write(avatar_b64)

                                log_sent_number(
                                    mes_number+1, gvars.MES_NUMBER_PATH)

                                avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            if "[Sticker]" in message:
                                chat['you'].append(
                                    {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                            elif "[Video]" in message:
                                chat['you'].append(
                                    {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})
                            else:
                                chat['you'].append(
                                    {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                        else:
                            if "[Sticker]" in message:
                                left_rate = 0.12
                                right_rate = 0.42
                                top_rate = 0.05
                                bottom_rate = 0.95
                            else:
                                left_rate = 0.125
                                right_rate = 0.85
                                top_rate = 0
                                bottom_rate = 0.92

                            if "[Video]" not in message:
                                iv = items[num-id].screenshot()
                                img = iv.convert("RGB") if hasattr(
                                    iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))
                                bounds = items[num-id].info['bounds']
                                width, height = bounds['right'] - \
                                    bounds['left'], bounds['bottom'] - \
                                    bounds['top']
                                left = bounds['left'] + int(width * left_rate)
                                right = bounds['left'] + \
                                    int(width * right_rate)
                            # top = bounds['top']
                                top = 0 + int(height * top_rate)
                            # bottom = bounds['bottom'] - int(height * 0.08)
                                bottom = 0 + int(height * bottom_rate)
                                cropped = img.crop((left, top, right, bottom))
                                cropped_small = cropped.filter(
                                    gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                                buf = gvars.io.BytesIO()
                                cropped_small.save(buf, format="PNG")
                            # output_path = "cropped_output.jpg"
                            # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                                avatar_b64 = gvars.base64.b64encode(
                                    buf.getvalue()).decode("ascii")

                                if not already_sent_number(gvars.MES_NUMBER_PATH):
                                    mes_number = 0
                                else:
                                    mes_number = read_sent_number(
                                        gvars.MES_NUMBER_PATH)
                                with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                    f.write(avatar_b64)

                                log_sent_number(
                                    mes_number+1, gvars.MES_NUMBER_PATH)

                                avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            else:
                                avatar_b64 = ""
                                try:
                                    iv = d(resourceId="com.zing.zalo:id/video_view")
                                    img = iv.screenshot()
                                    max_w, max_h = 200, 200
                                    # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                                    cropped_small = img

                                    buf = gvars.io.BytesIO()
                                    cropped_small.save(buf, format="PNG")
                                    # gvars.base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                                    avatar_b64 = gvars.base64.b64encode(
                                        buf.getvalue()).decode("ascii")
                                except Exception as e:
                                    print("Có lỗi trong quá trình lấy dữ liệu video ", e)

                                if not already_sent_number(gvars.MES_NUMBER_PATH):
                                    mes_number = 0
                                else:
                                    mes_number = read_sent_number(
                                        gvars.MES_NUMBER_PATH)
                                with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                                    f.write(avatar_b64)

                                log_sent_number(
                                    mes_number+1, gvars.MES_NUMBER_PATH)

                                avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                            if "[Sticker]" in message:
                                if gr_or_pvp == 'pvp':
                                    chat[f'{name_sender}'].append(
                                        {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                                else:
                                    if lack:
                                        chat_lack.append(
                                            {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                                        lack = False
                                    elif not lack and len(chat_lack) > 0:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                                            chat[f'{name_sender}'] = chat_lack + \
                                                chat[f'{name_sender}']
                                            chat_lack = []
                                            chat_lack_raw = []
                                    else:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                            elif "[Hình ảnh]" in message:
                                now = gvars.datetime.now()
                                print("Ngày:", now.day)
                                print("Tháng:", now.month)
                                print("Năm:", now.year)
                                print("Giờ:", now.hour)
                                print("Phút:", now.minute)
                                print("Giây:", now.second)
                                message = f"{message} {now.hour}:{now.minute}:{now.second} {now.day}/{now.month}/{now.year}"
                                if gr_or_pvp == 'pvp':
                                    chat[f'{name_sender}'].append(
                                        {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                                else:
                                    if lack:
                                        chat_lack.append(
                                            {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                                        lack = False
                                    elif not lack and len(chat_lack) > 0:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                                            chat[f'{name_sender}'] = chat_lack + \
                                                chat[f'{name_sender}']
                                            chat_lack = []
                                            chat_lack_raw = []
                                    else:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                            else:
                                if gr_or_pvp == 'pvp':
                                    chat[f'{name_sender}'].append(
                                        {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})
                                else:
                                    if lack:
                                        chat_lack.append(
                                            {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})
                                        lack = False
                                    elif not lack and len(chat_lack) > 0:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})
                                            chat[f'{name_sender}'] = chat_lack + \
                                                chat[f'{name_sender}']
                                            chat_lack = []
                                            chat_lack_raw = []
                                    else:
                                        if raw not in chat_lack_raw:
                                            chat[f'{name_sender}'].append(
                                                {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})
                    elif "Cuộc gọi thoại đi" in message:
                        if check_call == 2:
                            if len(chat['you']) > 0:
                                data_chat_box.append(chat)
                                # sender["you"] += 1
                                chat = {}
                                chat['you'] = []
                        chat['you'].append(
                            {"time": time_str, "type": "call", "data": message})
                        check_you_or_fr = 0
                        check_call = 1
                    elif "Cuộc gọi thoại đến" in message or "Bạn bị nhỡ Cuộc gọi thoại" in message:
                        if check_call == 1:
                            if len(chat[f'{name_sender}']) > 0:
                                data_chat_box.append(chat)
                                # id_f += 1
                                chat = {}
                                chat[f'{name_sender}'] = []
                        chat[f'{name_sender}'].append(
                            {"time": time_str, "type": "call", "data": message})
                        check_you_or_fr = 0
                        check_call = 2
                    elif "http" in message:
                        message = message.replace("html", "html\n")
                        message = message.replace("Tiktok", "\nTiktok")
                        if check_you_or_fr == 1:
                            chat['you'].append(
                                {"time": time_str, "type": "link", "data": message})
                        else:
                            if gr_or_pvp == 'pvp':
                                chat[f'{name_sender}'].append(
                                    {"time": time_str, "type": "link", "data": message})
                            else:
                                if lack:
                                    chat_lack.append(
                                        {"time": time_str, "type": "link", "data": message})
                                    lack = False
                                elif not lack and len(chat_lack) > 0:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": "link", "data": message})
                                        chat[f'{name_sender}'] = chat_lack + \
                                            chat[f'{name_sender}']
                                        chat_lack = []
                                        chat_lack_raw = []
                                else:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": "link", "data": message})
                    else:
                        if check_you_or_fr == 1:
                            chat['you'].append(
                                {"time": time_str, "type": "text", "data": message})
                            if len(items) == 1:
                                data_chat_box.append(chat)

                        else:
                            if gr_or_pvp == 'pvp':
                                chat[f'{name_sender}'].append(
                                    {"time": time_str, "type": "text", "data": message})
                                if len(items) == 1:
                                    data_chat_box.append(chat)
                            else:
                                if lack:
                                    chat_lack.append(
                                        {"time": time_str, "type": "text", "data": message})
                                    lack = False
                                elif not lack and len(chat_lack) > 0:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": "text", "data": message})
                                        chat[f'{name_sender}'] = chat_lack + \
                                            chat[f'{name_sender}']
                                        chat_lack = []
                                        chat_lack_raw = []
                                else:
                                    if raw not in chat_lack_raw:
                                        chat[f'{name_sender}'].append(
                                            {"time": time_str, "type": "text", "data": message})

            if not check:
                data_chat_box.append(chat)
                break
            current_last = items[0].text if items else None
            if current_last is None:
                break
            if current_last == previous_last:
                lines = [l for l in current_last.split("\n") if l.strip()]
                if len(lines) > 1 or not any(it in current_last for it in nope):
                    same_count += 1
                    if same_count >= 2:
                        # Thêm code lấy những phần tử còn thiếu
                        break
            else:
                same_count = 0
                previous_last = current_last

            # Swipe để load tin cũ
            w, h = d.window_size()
            # Cuộn lên (kéo từ trên xuống dưới)
            d.swipe(w // 2, int(h * 0.2), w // 2, int(h * 0.8), duration=0.8)
            gvars.eventlet.sleep(scroll_delay)
        except Exception as e:
            print("Đã gặp lỗi trong quá trình lấy lịch sử tin nhắn ", e)
    
    try:

        if check:
            ck_a = False
            for k in chat.keys():
                try:
                    if chat[k]:
                        ck_a = True
                except Exception as e:
                    print(e)

            if ck_a:
                data_chat_box.append(chat)
    except Exception as e:
        print("Lỗi khi thêm chat cuối cùng vào data_chat_box", e)

    rever_data_chat_box = data_chat_box[::-1]
    try:
        for i in range(len(rever_data_chat_box)):
            for key in rever_data_chat_box[i].keys():
                rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]
    except Exception as e:
        print("Lỗi khi đảo ngược thứ tự tin nhắn trong hộp chat", e)
    return rever_data_chat_box

def get_data_chat_boxes_1vs1_u2(d: gvars.u2.Device, time_and_mes, max_scroll: int = 5, scroll_delay: float = 1.0):
    """
    Trả về dict chứa hộp chat hiện có trong màn hình chat của Zalo Android.
    - div_child_selector: dict để tìm tab/conversation (ví dụ {'resourceId': '...', 'text': 'Tên bạn'})
    - device_url: đường dẫn để kết nối uiautomator2 (ví dụ '192.168.1.100:5555')
    - max_scroll: số lần swipe để load tin cũ.
    - scroll_delay: thời gian chờ giữa các lần swipe.
    """
    # d = run_start(d)
    data_chat_box = []
    chat = {}
    seen = set()
    lst_time_str = ""
    lst_message = ""
    check_first = False
    check_f_ac = False
    try:
        fr = d(resourceId="com.zing.zalo:id/action_bar_title").get_text()
        name_sender = fr
        chat[f'{name_sender}'] = []

        # if True:
        # 2) Tìm tất cả message bubble
        items = d.xpath("//android.view.ViewGroup[@text!='']").all()
        num = len(items) - 1
        # Đọc từ dưới lên trên (các tin mới trước)
        for id in range(num+1):
            raw = items[num-id].text or ""

            print(f"Tin nhắn thứ {id}: {raw}")

            if "đã đồng ý kết bạn" in raw:
                check_f_ac = True

            if raw in seen:
                continue

            if "Tin nhắn đã được thu hồi" in raw:
                continue

            check_1 = True
            if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                bounds = items[num-id].info['bounds']
                width, height = bounds['right'] - \
                    bounds['left'], bounds['bottom'] - bounds['top']
                # if height <= 400:
                #    continue
            formatted = gvars.date.today().strftime("%d/%m/%Y")
            raw = raw.replace("Hôm nay", formatted)
            if "[File]" in raw:
                raw = raw.split('…')[0]
                if time_and_mes['message'] != "":
                    if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                        check = False
                        check_1 = False
                        break
                mes = time_and_mes['message'].split("\n")
                if len(mes) > 1:
                    if mes[1] in raw:
                        check = False
                        check_1 = False
                        break
            seen.add(raw)
            lines = [l for l in raw.split("\n") if l.strip()]

            if time_and_mes['message'] in lines:
                if "[Hình ảnh]" not in time_and_mes['message']:
                    check = False
                    check_1 = False
                    break
                else:
                    if time_and_mes['time'] in lines or time_and_mes['time'] == "":
                        check = False
                        check_1 = False
                        break
            if "Gọi điện" in raw or "Nhắn tin" in raw:
                check = False
                check_1 = False

            if not check_1:
                break
            print(raw)
            print(time_and_mes)
            # Loại bỏ dòng 'Đã nhận'
            if lines and "Đã nhận" in lines[-1]:
                lines = lines[:-1]
                # check_you_or_fr = 1
            if lines and "Đã gửi" in lines[-1]:
                lines = lines[:-1]
            if lines and "Đã xem" in lines[-1]:
                lines = lines[:-1]
                check_you_or_fr = 1

            # Xử lý file/image
            if lines and "[File]" in raw:
                # time_str = lines[-1] if len(lines) > 1 else ''
                def has_time_token(s):
                    return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                if has_time_token(lines[0]) and has_time_token(lines[-1]):
                    time_str = lines[-1]
                    message = '\n'.join(lines[1:-1])

                elif has_time_token(lines[0]):
                    time_str = lines[0]
                    message = '\n'.join(lines[1:])

                elif has_time_token(lines[-1]):
                    time_str = lines[-1]
                    message = '\n'.join(lines[:-1])

                else:
                    time_str = ""
                    message = '\n'.join(lines)
                numm = message.split('\n')
                if len(numm) > 2:
                    message = "\n".join(numm[:2])

                formatted = gvars.date.today().strftime("%d/%m/%Y")
                time_str = time_str.replace("Hôm nay", formatted)
                typ = 'image' if any(
                    ext in message for ext in ('jpg', 'png')) else 'file'

                if typ == 'image':

                    iv = items[num-id].screenshot()
                    img = iv.convert("RGB") if hasattr(
                        iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))

                    bounds = items[num-id].info['bounds']
                    width, height = bounds['right'] - \
                        bounds['left'], bounds['bottom'] - bounds['top']

                    left = bounds['left'] + int(width * 0.125)
                    right = bounds['left'] + int(width * 0.85)
                    # top = bounds['top']
                    top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                    bottom = int(height * 0.92)

                    cropped = img.crop((left, top, right, bottom))

                    cropped_small = cropped.filter(
                        gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                    buf = gvars.io.BytesIO()
                    cropped_small.save(buf, format="PNG")

                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                    avatar_b64 = gvars.base64.b64encode(
                        buf.getvalue()).decode("ascii")

                    if not already_sent_number(gvars.MES_NUMBER_PATH):
                        mes_number = 0
                    else:
                        mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                    with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                        f.write(avatar_b64)

                    log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                    avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    chat[f'{name_sender}'].append(
                        {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})

                else:
                    chat[f'{name_sender}'].append(
                        {"time": time_str, "type": typ, "data": message, "file_data": ""})

            else:
                # Xác định time và message
                time_str = ''
                message = ''
                if lines:
                    # kiểm tra dấu giờ phút
                    def has_time_token(s):
                        return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                    if has_time_token(lines[0]) and has_time_token(lines[-1]):
                        time_str = lines[-1]
                        message = '\n'.join(lines[1:-1])

                    elif has_time_token(lines[0]):
                        time_str = lines[0]
                        message = '\n'.join(lines[1:])

                    elif has_time_token(lines[-1]):
                        time_str = lines[-1]
                        message = '\n'.join(lines[:-1])

                    else:
                        time_str = ""
                        message = '\n'.join(lines)

                    formatted = gvars.date.today().strftime("%d/%m/%Y")
                    time_str = time_str.replace("Hôm nay", formatted)

                if "Tin nhắn đã được thu hồi" in message:
                    pass
                elif "[Hình ảnh]" in message or "[Sticker]" in message or "[Video]" in message:

                    if "[Sticker]" in message:
                        left_rate = 0.12
                        right_rate = 0.42
                        top_rate = 0.05
                        bottom_rate = 0.95
                    else:
                        left_rate = 0.125
                        right_rate = 0.85
                        top_rate = 0
                        bottom_rate = 0.92

                    if "[Video]" not in message:
                        iv = items[num-id].screenshot()
                        img = iv.convert("RGB") if hasattr(
                            iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        left = bounds['left'] + int(width * left_rate)
                        right = bounds['left'] + int(width * right_rate)
                    # top = bounds['top']
                        top = 0 + int(height * top_rate)
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = 0 + int(height * bottom_rate)
                        cropped = img.crop((left, top, right, bottom))
                        cropped_small = cropped.filter(
                            gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                        buf = gvars.io.BytesIO()
                        cropped_small.save(buf, format="PNG")
                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = gvars.base64.b64encode(
                            buf.getvalue()).decode("ascii")

                        if not already_sent_number(gvars.MES_NUMBER_PATH):
                            mes_number = 0
                        else:
                            mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                        with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                            f.write(avatar_b64)

                        log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                        avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    else:
                        avatar_b64 = ""
                        try:
                            iv = d(resourceId="com.zing.zalo:id/video_view")
                            img = iv.screenshot()
                            max_w, max_h = 200, 200
                            # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                            cropped_small = img

                            buf = gvars.io.BytesIO()
                            cropped_small.save(buf, format="PNG")
                            # gvars.base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                            avatar_b64 = gvars.base64.b64encode(
                                buf.getvalue()).decode("ascii")
                        except Exception as e:
                            print("Đã có lỗi xảy ra trong quá trình lấy dữ liệu video ", e)

                        if not already_sent_number(gvars.MES_NUMBER_PATH):
                            mes_number = 0
                        else:
                            mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                        with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                            f.write(avatar_b64)

                        log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                        avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    if "[Sticker]" in message:
                        chat[f'{name_sender}'].append(
                            {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})
                    elif "[Hình ảnh]" in message:
                        chat[f'{name_sender}'].append(
                            {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})
                    else:
                        chat[f'{name_sender}'].append(
                            {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})

                elif "Cuộc gọi thoại đi" in message:
                    pass
                elif "Cuộc gọi thoại đến" in message or "Bạn bị nhỡ Cuộc gọi thoại" in message:
                    pass
                elif "http" in message:
                    message = message.replace("html", "html\n")
                    message = message.replace("Tiktok", "\nTiktok")
                    chat[f'{name_sender}'].append(
                        {"time": time_str, "type": "link", "data": message})

                else:
                    chat[f'{name_sender}'].append(
                        {"time": time_str, "type": "text", "data": message})
            if not check_first:
                lst_time_str = time_str
                lst_message = message
                check_first = True
    except Exception as e:
        print("Đã gặp lỗi trong quá trình lấy lịch sử chat 1vs1 ", e)

    if len(chat[f'{name_sender}']) > 0:
        data_chat_box.append(chat)

    rever_data_chat_box = data_chat_box[::-1]
    for i in range(len(rever_data_chat_box)):
        for key in rever_data_chat_box[i].keys():
            rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]

    return rever_data_chat_box, lst_time_str, lst_message, check_f_ac


def get_data_chat_boxes_gr_u2(d: gvars.u2.Device, time_and_mes, list_mems, max_scroll: int = 5, scroll_delay: float = 1.0):
    """
    Trả về dict chứa hộp chat hiện có trong màn hình chat của Zalo Android.
    - div_child_selector: dict để tìm tab/conversation (ví dụ {'resourceId': '...', 'text': 'Tên bạn'})
    - device_url: đường dẫn để kết nối uiautomator2 (ví dụ '192.168.1.100:5555')
    - max_scroll: số lần swipe để load tin cũ.
    - scroll_delay: thời gian chờ giữa các lần swipe.
    """
    # d = run_start(d)
    print("Thành viên trong nhóm là: ", list_mems)
    name_members = [l['name_member'] for l in list_mems]
    data_chat_box = []
    chat = {}
    seen = set()
    lst_time_str = ""
    lst_message = ""
    check_first = False
    list_data_chat = []
    name_sender = ""
    # fr = d(resourceId="com.zing.zalo:id/action_bar_title").get_text()
    # name_sender = fr
    # chat[f'{name_sender}'] = []

#    if True:
    # 2) Tìm tất cả message bubble
    try:
        items = d.xpath("//android.view.ViewGroup[@text!='']").all()
        num = len(items) - 1
        ck_sender = False
        # Đọc từ dưới lên trên (các tin mới trước)
        for id in range(num+1):
            raw = items[num-id].text or ""

            print("Dữ liệu đoạn chat cào được là", raw)

            if raw in seen:
                continue

            if "Tin nhắn đã được thu hồi" in raw:
                continue

            check_1 = True
            if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                bounds = items[num-id].info['bounds']
                width, height = bounds['right'] - \
                    bounds['left'], bounds['bottom'] - bounds['top']
                # if height <= 400:
                #    continue
            formatted = gvars.date.today().strftime("%d/%m/%Y")
            raw = raw.replace("Hôm nay", formatted)
            if "[File]" in raw:
                raw = raw.split('…')[0]
                if time_and_mes['message'] != "":
                    if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                        check = False
                        check_1 = False
                        break
                mes = time_and_mes['message'].split("\n")
                if len(mes) > 1:
                    if mes[1] in raw:
                        check = False
                        check_1 = False
                        break
            seen.add(raw)
            lines = [l for l in raw.split("\n") if l.strip()]

            if time_and_mes['message'] in lines:
                if "[Hình ảnh]" not in time_and_mes['message']:
                    check = False
                    check_1 = False
                    break
                else:
                    if time_and_mes['time'] in lines or time_and_mes['time'] == "":
                        check = False
                        check_1 = False
                        break
            if "Gọi điện" in raw or "Nhắn tin" in raw:
                check = False
                check_1 = False

            if not check_1:
                break
            print(raw)
            print(time_and_mes)
            # Loại bỏ dòng 'Đã nhận'
            if lines and "Đã nhận" in lines[-1]:
                lines = lines[:-1]
                # check_you_or_fr = 1
            if lines and "Đã gửi" in lines[-1]:
                lines = lines[:-1]
            if lines and "Đã xem" in lines[-1]:
                lines = lines[:-1]
                check_you_or_fr = 1

            # Xử lý file/image
            if lines and "[File]" in raw:
                # time_str = lines[-1] if len(lines) > 1 else ''
                def has_time_token(s):
                    return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                if has_time_token(lines[0]) and has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[1] in name_members:
                        name_sender = lines[1]
                        ck_sender = True
                        message = '\n'.join(lines[2:-1])
                    else:
                        message = '\n'.join(lines[1:-1])

                elif has_time_token(lines[0]):
                    time_str = lines[0]
                    if lines[1] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[2:])
                    else:
                        message = '\n'.join(lines[1:])

                elif has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[0] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:-1])
                    else:
                        message = '\n'.join(lines[:-1])

                else:
                    time_str = ""
                    if lines[0] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:])
                    else:
                        message = '\n'.join(lines)

                numm = message.split('\n')
                if len(numm) > 2:
                    message = "\n".join(numm[:2])

                formatted = gvars.date.today().strftime("%d/%m/%Y")
                time_str = time_str.replace("Hôm nay", formatted)
                typ = 'image' if any(
                    ext in message for ext in ('jpg', 'png')) else 'file'

                avatar_b64 = ""

                if typ == 'image':

                    iv = items[num-id].screenshot()
                    img = iv.convert("RGB") if hasattr(
                        iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))

                    bounds = items[num-id].info['bounds']
                    width, height = bounds['right'] - \
                        bounds['left'], bounds['bottom'] - bounds['top']

                    left = bounds['left'] + int(width * 0.125)
                    right = bounds['left'] + int(width * 0.85)
                    # top = bounds['top']
                    top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                    bottom = int(height * 0.92)

                    cropped = img.crop((left, top, right, bottom))

                    cropped_small = cropped.filter(
                        gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                    buf = gvars.io.BytesIO()
                    cropped_small.save(buf, format="PNG")

                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                    avatar_b64 = gvars.base64.b64encode(
                        buf.getvalue()).decode("ascii")

                    if not already_sent_number(gvars.MES_NUMBER_PATH):
                        mes_number = 0
                    else:
                        mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                    with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                        f.write(avatar_b64)

                    log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                    avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    list_data_chat.append(
                        {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})

                    if ck_sender:
                        chat[f'{name_sender}'] = list_data_chat
                        list_data_chat = []
                        ck_sender = False

                        data_chat_box.append(chat)
                        chat = {}

                else:

                    list_data_chat.append(
                        {"time": time_str, "type": typ, "data": message, "file_data": avatar_b64})

                    if ck_sender:
                        chat[f'{name_sender}'] = list_data_chat
                        list_data_chat = []
                        ck_sender = False

                        data_chat_box.append(chat)
                        chat = {}

            else:
                # Xác định time và message
                time_str = ''
                message = ''
                if lines:
                    # kiểm tra dấu giờ phút
                    def has_time_token(s):
                        return any(len(tok) == 5 and tok[2] == ':' for tok in s.split())
                if has_time_token(lines[0]) and has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[1] in name_members:
                        name_sender = lines[1]
                        ck_sender = True
                        message = '\n'.join(lines[2:-1])
                    else:
                        message = '\n'.join(lines[1:-1])

                elif has_time_token(lines[0]):
                    time_str = lines[0]
                    if lines[1] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[2:])
                    else:
                        message = '\n'.join(lines[1:])

                elif has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[0] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:-1])
                    else:
                        message = '\n'.join(lines[:-1])

                else:
                    time_str = ""
                    if lines[0] in name_members:
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:])
                    else:
                        message = '\n'.join(lines)

                    formatted = gvars.date.today().strftime("%d/%m/%Y")
                    time_str = time_str.replace("Hôm nay", formatted)

                if "Tin nhắn đã được thu hồi" in message:
                    pass
                elif "[Hình ảnh]" in message or "[Sticker]" in message or "[Video]" in message:

                    if "[Sticker]" in message:
                        left_rate = 0.12
                        right_rate = 0.42
                        top_rate = 0.05
                        bottom_rate = 0.95
                    else:
                        left_rate = 0.125
                        right_rate = 0.85
                        top_rate = 0
                        bottom_rate = 0.92

                    if "[Video]" not in message:
                        iv = items[num-id].screenshot()
                        img = iv.convert("RGB") if hasattr(
                            iv, "convert") else gvars.Image.open(gvars.io.BytesIO(iv))
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        left = bounds['left'] + int(width * left_rate)
                        right = bounds['left'] + int(width * right_rate)
                    # top = bounds['top']
                        top = 0 + int(height * top_rate)
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = 0 + int(height * bottom_rate)
                        cropped = img.crop((left, top, right, bottom))
                        cropped_small = cropped.filter(
                            gvars.ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

                        buf = gvars.io.BytesIO()
                        cropped_small.save(buf, format="PNG")
                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = gvars.base64.b64encode(
                            buf.getvalue()).decode("ascii")

                        if not already_sent_number(gvars.MES_NUMBER_PATH):
                            mes_number = 0
                        else:
                            mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                        with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                            f.write(avatar_b64)

                        log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                        avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    else:
                        avatar_b64 = ""
                        try:
                            iv = d(resourceId="com.zing.zalo:id/video_view")
                            img = iv.screenshot()
                            max_w, max_h = 200, 200
                            # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                            cropped_small = img

                            buf = gvars.io.BytesIO()
                            cropped_small.save(buf, format="PNG")
                            # gvars.base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                            avatar_b64 = gvars.base64.b64encode(
                                buf.getvalue()).decode("ascii")
                        except Exception as e:
                            print("Đã có lỗi xảy ra trong quá trình lấy dữ liệu video ", e)

                        if not already_sent_number(gvars.MES_NUMBER_PATH):
                            mes_number = 0
                        else:
                            mes_number = read_sent_number(gvars.MES_NUMBER_PATH)
                        with open(f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt", "w", encoding="utf-8") as f:
                            f.write(avatar_b64)

                        log_sent_number(mes_number+1, gvars.MES_NUMBER_PATH)

                        avatar_b64 = f"{gvars.IMAGE_FILE_DATA_PATH}/mes_{mes_number}.txt"

                    if "[Sticker]" in message:
                        list_data_chat.append(
                            {"time": time_str, "type": "sticker", "data": message, "sticker_data": avatar_b64})

                        if ck_sender:
                            chat[f'{name_sender}'] = list_data_chat
                            list_data_chat = []
                            ck_sender = False

                            data_chat_box.append(chat)
                            chat = {}
                    elif "[Hình ảnh]" in message:
                        list_data_chat.append(
                            {"time": time_str, "type": "image", "data": message, "image_data": avatar_b64})

                        if ck_sender:
                            chat[f'{name_sender}'] = list_data_chat
                            list_data_chat = []
                            ck_sender = False

                            data_chat_box.append(chat)
                            chat = {}
                    else:
                        list_data_chat.append(
                            {"time": time_str, "type": "video", "data": message, "video_data": avatar_b64})

                        if ck_sender:
                            chat[f'{name_sender}'] = list_data_chat
                            list_data_chat = []
                            ck_sender = False

                            data_chat_box.append(chat)
                            chat = {}

                elif "Cuộc gọi thoại đi" in message:
                    pass
                elif "Cuộc gọi thoại đến" in message or "Bạn bị nhỡ Cuộc gọi thoại" in message:
                    pass
                elif "http" in message:
                    message = message.replace("html", "html\n")
                    message = message.replace("Tiktok", "\nTiktok")

                    list_data_chat.append(
                        {"time": time_str, "type": "link", "data": message})

                    if ck_sender:
                        chat[f'{name_sender}'] = list_data_chat
                        list_data_chat = []
                        ck_sender = False

                        data_chat_box.append(chat)
                        chat = {}

                else:
                    list_data_chat.append(
                        {"time": time_str, "type": "text", "data": message})

                    if ck_sender:
                        chat[f'{name_sender}'] = list_data_chat
                        list_data_chat = []
                        ck_sender = False

                        data_chat_box.append(chat)
                        chat = {}

            if not check_first:
                lst_time_str = time_str
                lst_message = message
                check_first = True
    except Exception as e:
        print("Đã xảy ra lỗi trong quá trình lấy lịch sử chat ", e)

#    if len(chat[f'{name_sender}']) > 0:
#        data_chat_box.append(chat)
    ck_st = False
    if len(list_data_chat) > 0:
        ck_st = True
        data_chat_box = list_data_chat
        rever_data_chat_box = data_chat_box[::-1]
    else:
        rever_data_chat_box = data_chat_box[::-1]
        for i in range(len(rever_data_chat_box)):
            for key in rever_data_chat_box[i].keys():
                rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]

    return rever_data_chat_box, lst_time_str, lst_message, ck_st


'''
def get_list_emoji_sticker_u2(d: gvars.u2.Device, id_device="", max_emoji_sticker: int = 200, scroll_delay: float = 1.0, retire=3, has_update=False, friend_name=[], num_phone_zalo="", list_friend_old=[]):
    """
    Lấy toàn bộ bạn bè từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_friends: giới hạn tối đa số bạn bè thu thập
    """
    emoji_sticker = []
    seen = set()
    previous_last = ""
    same_count = 0

    try:
        d.xpath('//*[@resource-id="com.zing.zalo:id/chat_input_bar_container"]/android.widget.FrameLayout[1]/android.widget.LinearLayout[1]').click()
        gvars.eventlet.sleep(1.0)
        d(resourceId="com.zing.zalo:id/blc_input_emoji_tab").click()
    except Exception as e:
        print(e)

    try:
        # 2) Lặp scroll & thu thập
        while len(emoji_sticker) < max_emoji_sticker:
            # 2.1 lấy tất cả item bạn bè đang hiển thị
            # giả sử d là đối tượng uiautomator2 device

            # tìm tất cả LinearLayout con của emoticon_selector_grid
            elems = d.xpath(
                '//*[@resource-id="com.zing.zalo:id/emoticon_selector_grid"]/android.widget.LinearLayout')
            for ll in elems:
                # trong mỗi LinearLayout, tìm các LinearLayout bên trong
                sub_lls = ll.xpath('./android.widget.LinearLayout')
                for sub in sub_lls:
                    # trong mỗi sub-LinearLayout, tìm ImageView đầu tiên
                    img = sub.xpath('./android.widget.ImageView[1]')
                    if img.exists:
                        img.click()

            if len(friends) >= max_friends:
                break

            # Kiểm tra có còn dữ liệu mới không
            if items:
                last_raw = items[-1].text or ""
                if last_raw == previous_last:
                    same_count += 1
                    if same_count >= 2:
                        break
                else:
                    same_count = 0
                    previous_last = last_raw

            # 2.2 scroll lên để load thêm
            w, h = d.window_size()
            d.swipe(w//2, int(h*0.8), w//2, int(h*0.2), duration=0.8)
            gvars.eventlet.sleep(scroll_delay)
    except Exception as e:
        print(e)
    return friends
'''


def get_list_members_group_u2(d: gvars.u2.Device, max_scroll: int = 100, scroll_delay: float = 1.0):
    # 1) Click vào cuộc nhóm

    # 2) Lấy tên nhóm từ thanh title
    # name = d(resourceId="com.zing.zalo:id/action_bar_title").get_text() or ""

    # 3) Mở navigation drawer và click "Xem thành viên"
    d(resourceId="com.zing.zalo:id/menu_drawer").click()
    gvars.eventlet.sleep(1.0)
    try:
        d.xpath(
            "//android.widget.FrameLayout[contains(@text, 'Xem thành viên')]").click()
    except Exception as e:
        d.swipe_ext(gvars.u2.Direction.FORWARD, scale=0.3)
        gvars.eventlet.sleep(1.0)
        d.xpath(
            "//android.widget.FrameLayout[contains(@text, 'Xem thành viên')]").click()
    gvars.eventlet.sleep(1.0)

    # 4) Chuẩn bị lưu kết quả
    list_mems = []
    previous_last = ""
    same_count = 0
    scrolls = 0
    check_mems = True
    seen = set()

    # 5) Lặp scroll lấy member
    while scrolls < max_scroll:
        scrolls += 1

        # Lấy tất cả các item trong RecyclerView
        items = d.xpath(
            "//*[@resource-id='com.zing.zalo:id/contact_list']"
            "/android.widget.FrameLayout"
        ).all()

        # Xử lý từng item
        for it in items:
            raw = it.text or ""
            if "Gợi ý thêm thành viên" in raw or "Thành viên" in raw:
                continue
            parts = raw.split("\n")
            name_member = parts[0]
            if name_member in seen:
                continue
            seen.add(name_member)

            role = ""
            if len(parts) > 1:
                if "Trưởng nhóm" in raw:
                    role = "Trưởng nhóm"
                    # check_mems = False
                elif "Trưởng cộng đồng" in raw:
                    role = "Trưởng cộng đồng"
                    # check_mems = False
                elif "Phó cộng đồng" in raw:
                    role = "Phó cộng đồng"
                    # check_mems = False
            list_mems.append({"name_member": name_member, "role": role})

        # Kiểm tra xem có còn mới không
        last_raw = items[-1].text if items else ""
        if last_raw == previous_last:
            same_count += 1
            if same_count >= 2:
                break
        else:
            same_count = 0
            previous_last = last_raw

        # Swipe lên để load thêm
        w, h = d.window_size()
        start_x, start_y = w // 2, int(h * 0.8)
        end_x, end_y = w // 2, int(h * 0.2)
        d.swipe(start_x, start_y, end_x, end_y, duration=0.8)
        gvars.eventlet.sleep(scroll_delay)

    return list_mems, check_mems


def api_get_list_friend(data_body, has_first_update):
    # data_body = gvars.request.form
    new_id = data_body['num_phone_zalo']
    # global now_phone_zalo
    # global device_connect
    # now_phone_zalo = new_id
    gvars.list_socket_call.append("get_list_friend")
    num_phone_zalo = new_id

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print("Có lỗi trong quá trình lấy thông tin tài khoản zalo")
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    list_friend_old = document['list_friend']
    friend_name = [l['name'] for l in list_friend_old]
    try:
        d = gvars.u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối", id_device)
        gvars.device_connect[id_device] = False
        return [], True

    if (num_phone_zalo in gvars.dict_status_zalo.keys()):

        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return [], True
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return [], True
            else:
                gvars.dict_status_zalo[num_phone_zalo] = "get_list_friend"
                update_again = False
                result = []
                try:
                    result = get_list_friends_u2(
                        d, max_friends=1500, has_update=has_first_update, friend_name=friend_name, num_phone_zalo=num_phone_zalo, list_friend_old=list_friend_old)
                    print("Kết quả trả về là ", result)

                except Exception as e:
                    print("Lỗi xaỷ ra khi cào bb", e)
                    result = list_friend_old
                    update_again = True
                    
                gvars.dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result, update_again


def api_get_list_group(data_body, list_mems, check_mems):
    # data_body = gvars.request.form
    new_id = data_body['num_phone_zalo']
    gvars.list_socket_call.append("get_list_group")
    # global now_phone_zalo
    # global device_connect
    num_phone_zalo = new_id
    # now_phone_zalo = num_phone_zalo

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    try:
        d = gvars.u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        gvars.device_connect[id_device] = False
        return [], True
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            return [], True
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                return [], True
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            else:

                gvars.dict_status_zalo[num_phone_zalo] = "get_list_friend"
                result = []
                update_again = False
                try:
                    result = get_list_groups_u2(
                        d, list_mems=list_mems, check_mems=check_mems, max_groups=300)
                    data_update = {"list_group": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    update_again = True
                gvars.dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result, update_again


def api_get_list_invite_friend(data_body):
    # data_body = gvars.request.form
    new_id = data_body['num_phone_zalo']
    # global now_phone_zalo
    # global device_connect
    gvars.list_socket_call.append("get_list_invite_friend")
    num_phone_zalo = new_id
    # now_phone_zalo = num_phone_zalo

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']

    try:
        d = gvars.u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        gvars.device_connect[id_device] = False
        return [], True
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            return [], True
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                return [], True
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            else:

                gvars.dict_status_zalo[num_phone_zalo] = "get_list_friend"
                update_again = False
                result = []
                try:
                    result = get_list_invite_friends_u2(d)
                    data_update = {"list_invite_friend": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    update_again = True
                gvars.dict_status_zalo[num_phone_zalo] = ""
                # if len(result) > 0:
                # result = [box['name'] for box in result]
                return result, update_again


def api_update_list_prior_chat_boxes(data_body, tag_name={}, data_chat_boxes={}, friend_or_nots={}, max_chat_boxes=2000, scroll_or_not=True):
    # data_body = gvars.request.form
    new_id = data_body['num_phone_zalo']
    gvars.list_socket_call.append("get_list_prior_chat_boxes")
    num_phone_zalo = new_id

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    try:
        d = gvars.u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối", id_device)
        gvars.device_connect[id_device] = False
        return [], True
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return [], True
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return [], True
            else:

                gvars.dict_status_zalo[num_phone_zalo] = "update_list_prior_chat_boxes"
                update_again = False
                result = []
                try:
                    result = get_list_prior_chat_boxes_u2(
                        d, tag_name=tag_name, data_chat_boxes=data_chat_boxes, friend_or_nots=friend_or_nots, max_chat_boxes=max_chat_boxes, scroll_or_not=scroll_or_not)
                    data_update = {"list_prior_chat_boxes": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    update_again = True
                gvars.dict_status_zalo[num_phone_zalo] = ""

                return result, update_again


def api_update_list_unseen_chat_boxes(data):
    # data_body = gvars.request.form
    new_id = data['num_phone_zalo']
    gvars.list_socket_call.append("update_list_unseen_chat_boxes")
    num_phone_zalo = new_id

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    try:
        d = gvars.u2.connect(id_device)
        gvars.device_connect[id_device] = True
    except Exception as e:
        print("Thiết bị đã ngắt kết nối", id_device)
        gvars.device_connect[id_device] = False
        return [], True
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            return [], True
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return [], True
            else:
                gvars.dict_status_zalo[num_phone_zalo] = "update_list_unseen_chat_boxes"
                result = []
                update_again = False
                try:
                    result = get_list_unseen_chat_boxes_u2(
                        d, max_chat_boxes=50)
                    unseen_boxes = [box['name'] for box in result]
                    data_update = {"list_unseen_chat_boxes": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                    try:
                        #        print(document)
                        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r', encoding='utf-8') as f:
                            data = gvars.json.load(f)
                        for id in range(len(data)):
                            #            print(document[domain])
                            if data[id]['num_phone_zalo'] == num_phone_zalo:
                                for it in range(len(data[id]['list_prior_chat_boxes'])):
                                    if data[id]['list_prior_chat_boxes'][it]['name'] in unseen_boxes:
                                        data[id]['list_prior_chat_boxes'][it]['status'] = "unseen"

                        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}.json', 'w', encoding='utf-8') as f:
                            gvars.json.dump(
                                data, f, ensure_ascii=False, indent=4)

                    except Exception as e:
                        print(e)
                        return [], True

                except Exception as e:
                    result = []
                    update_again = True
                gvars.dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result, update_again


def api_update_data_one_chat_box(data, gr_or_pvp="pvp", on_chat=False, update=False):
    # data_body = gvars.request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    gvars.list_socket_call.append("get_data_one_box_chat")
    num_phone_zalo = new_id
    num_phone_ntd = None
    # global device_connect

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']

    try:
        d = gvars.u2.connect(id_device)
        # global gvars.device_connect
        gvars.device_connect[id_device] = True
    except Exception as e:
        print("Thiết bị đã ngắt kết nối", id_device)
        gvars.device_connect[id_device] = False
        return False
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                gvars.dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                if 'list_prior_chat_boxes' not in document.keys():
                    document['list_prior_chat_boxes'] = []
                list_prior_chat_boxes = document['list_prior_chat_boxes']
                check_pvp_or_gr = ""
                result = []
                try:
                    if not on_chat:
                        d.app_start("com.zing.zalo", stop=True)
                        gvars.eventlet.sleep(1.0)
                        if num_phone_ntd != None:
                            data_ntd = num_phone_ntd
                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            gvars.eventlet.sleep(1.0)
                            d(resourceId="com.zing.zalo:id/btn_search_result").click()
                            gvars.eventlet.sleep(0.5)
                            try:
                                btn = d(
                                    resourceId="com.zing.zalo:id/btn_send_message")
                                if btn.exists:
                                    btn.click()
                                    gvars.eventlet.sleep(0.5)
                            except Exception:
                                pass
                            d.xpath('//*[@text="Đóng"]')
                            gvars.eventlet.sleep(1.0)
                            check_pvp_or_gr = "pvp"
                            if d(textContains="Đóng").exists:
                                d(textContains="Đóng").click()
                                gvars.eventlet.sleep(0.5)
                            data_ntd = d(
                                resourceId="com.zing.zalo:id/action_bar_title").get_text()

                        else:
                            data_ntd = name_ntd
                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            gvars.eventlet.sleep(1.0)
                            '''
                            elements = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            if elements:
                                elements[0].click()
                            gvars.eventlet.sleep(1.0)
                            '''
                            try:
                                chat_list = d.xpath(
                                    '//*[@resource-id="com.zing.zalo:id/btn_search_result"]').all()

                                # if len(chat_num) > 0:
                                for item in chat_list:
                                    raw = item.text
                                    print("Raw là", raw)
                                    lines = [l for l in raw.split(
                                        "\n") if l.strip()]
                                    print(lines)
                                    if lines[0] == data_ntd:
                                        print("Có trùng khớp")
                                        item.click()
                                        break

                                gvars.eventlet.sleep(1.0)
                            except Exception as e:
                                print('Ellipsis')
                                pass
                            '''
                     for friend in list_friend:
                       if data_ntd == friend['name']:
                           check_pvp_or_gr = "pvp"
                           break
                     for 
                     if check_pvp_or_gr  == "":
                       return  jsonify({"status" : "Không tìm thấy tên NTD hoặc nhóm phù hợp"})
                     '''
                    data_ntd = name_ntd
                    check = False
                    pick = -1
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == data_ntd:
                            pick = id
                            check = True
                    if not check:
                        list_prior_chat_boxes.append(
                            {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": ""})
                        time_and_mes = {'time': "",  "message": ""}
                        data_chat_box = []
                    else:
                        if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == "":
                            list_prior_chat_boxes[pick]['data_chat_box'] = ""
                            data_chat_box = []
                            time_and_mes = {'time': "", "message": ""}
                        else:
                            try:
                                data_chat_box = load_data_chat_box_json(
                                    list_prior_chat_boxes[pick]['data_chat_box'])
                                last_data = data_chat_box[-1]
                                last_data_mes = {}
                                for it in last_data.keys():
                                    last_data_mes = last_data[it][-1]
                                time_and_mes = {
                                    "time": last_data_mes['time'], "message": last_data_mes['data']}
                            except Exception as e:
                                data_chat_box = []
                                print("Không lấy được lịch sử chat ", e)
                                time_and_mes = {'time': "", "message": ""}

                    raw_result = get_data_chat_boxes_u2(
                        d, gr_or_pvp, time_and_mes)
                    result = [r for r in raw_result if r]

                    friend_or_not = "no"
                    if gr_or_pvp == 'pvp':
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

                    if len(result) > 0:
                        # if not update:
                        data_chat_box = data_chat_box + result
                        list_prior_chat_boxes[pick]['data_chat_box'] = dump_data_chat_box_json(
                            list_prior_chat_boxes[pick]['data_chat_box'], data_chat_box)

                        if gr_or_pvp == 'pvp':
                            list_prior_chat_boxes[pick]['friend_or_not'] = friend_or_not

                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                        update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

                except Exception as e:
                    print(e)
                gvars.dict_status_zalo[num_phone_zalo] = ""
                return result


def api_update_data_1vs1_chat_box(d: gvars.u2.Device, data, document):

    # data_body = gvars.request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    num_phone_zalo = new_id
    id_device = document['id_device']
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '':
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:

                # gvars.dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                if 'list_prior_chat_boxes' not in document.keys():
                    document['list_prior_chat_boxes'] = []
                list_prior_chat_boxes = document['list_prior_chat_boxes']
                list_friend = document['list_friend']
                data_ntd = name_ntd
                check = False
                pick = -1
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == data_ntd:
                        pick = id
                        check = True
                if not check:
                    list_prior_chat_boxes.append(
                        {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": ""})
                    time_and_mes = {'time': "",  "message": ""}
                    data_chat_box = []
                else:
                    if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == "":
                        list_prior_chat_boxes[pick]['data_chat_box'] = ""
                        time_and_mes = {'time': "", "message": ""}
                        data_chat_box = []

                    else:
                        try:
                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[pick]['data_chat_box'])
                            last_data = data_chat_box[-1]
                            last_data_mes = {}
                            for it in last_data.keys():
                                last_data_mes = last_data[it][-1]
                            time_and_mes = {
                                "time": last_data_mes['time'], "message": last_data_mes['data']}
                        except Exception as e:
                            data_chat_box = []
                            print("Không lấy được lịch sử chat ", e)
                            time_and_mes = {'time': "", "message": ""}
                raw_result, lst_time_str, lst_message, check_f_ac = get_data_chat_boxes_1vs1_u2(
                    d, time_and_mes)
                result = [r for r in raw_result if r]
                # retr = result

                if len(result) > 0:
                    data_chat_box = data_chat_box + result
                    list_prior_chat_boxes[pick]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[pick]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes[pick]['time'] = lst_time_str
                    list_prior_chat_boxes[pick]['message'] = lst_message
                    list_prior_chat_boxes[pick]['status'] = "unseen"
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(pick))
                    if check_f_ac:
                        ava = ""
                        if 'ava' in list_prior_chat_boxes[pick].keys():
                            ava = list_prior_chat_boxes[pick]['ava']
                        list_friend_name = [l['name'] for l in list_friend]
                        if data_ntd not in list_friend_name:
                            list_friend.append({"name": data_ntd, "ava": ava})
                            data_update = {"num_phone_zalo": num_phone_zalo,
                                           "list_prior_chat_boxes": list_prior_chat_boxes, "list_friend": list_friend}
                        else:
                            data_update = {"num_phone_zalo": num_phone_zalo,
                                           "list_prior_chat_boxes": list_prior_chat_boxes}
                    else:
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

                return result


def api_update_data_gr_chat_box(d: gvars.u2.Device, data, document):
    # data_body = gvars.request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    num_phone_zalo = new_id
    user_name = document['name']
    id_device = document['id_device']
    list_group = document['list_group']

    list_group_name = [g['name'] for g in list_group]
    list_mems = []
    for group in list_group:
        if group['name'] == name_ntd:
            if 'list_mems' in group.keys():
                list_mems = group['list_mems']
                break
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '':
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:

                # gvars.dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                if 'list_prior_chat_boxes' not in document.keys():
                    document['list_prior_chat_boxes'] = []
                list_prior_chat_boxes = document['list_prior_chat_boxes']
                data_ntd = name_ntd
                check = False
                pick = -1
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == data_ntd:
                        print("Có tồn tại nhà tuyển dụng này nhé")
                        pick = id
                        check = True
                if not check:
                    list_prior_chat_boxes.append(
                        {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": ""})
                    time_and_mes = {'time': "",  "message": ""}
                    data_chat_box = []
                else:

                    if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == "":
                        list_prior_chat_boxes[pick]['data_chat_box'] = ""
                        time_and_mes = {'time': "", "message": ""}
                        data_chat_box = []

                    else:
                        try:

                            data_chat_box = load_data_chat_box_json(
                                list_prior_chat_boxes[pick]['data_chat_box'])
                            last_data = data_chat_box[-1]
                            last_data_mes = {}
                            for it in last_data.keys():
                                last_data_mes = last_data[it][-1]
                            time_and_mes = {
                                "time": last_data_mes['time'], "message": last_data_mes['data']}
                        except Exception as e:
                            data_chat_box = []
                            print("Không lấy được lịch sử chat ", e)
                            time_and_mes = {'time': "", "message": ""}
                raw_result, lst_time_str, lst_message, ck_sender = get_data_chat_boxes_gr_u2(
                    d, time_and_mes, list_mems)
                result = [r for r in raw_result if r]

                if len(result) > 0:
                    if not ck_sender:
                        for res in result:
                            data_chat_box.append(
                                res)
                    else:
                        for k in data_chat_box[-1].keys():
                            for res in result:
                                data_chat_box[-1][k].append(
                                    res)

                    list_prior_chat_boxes[pick]['data_chat_box'] = dump_data_chat_box_json(
                        list_prior_chat_boxes[pick]['data_chat_box'], data_chat_box)
                    list_prior_chat_boxes[pick]['time'] = lst_time_str
                    list_prior_chat_boxes[pick]['message'] = lst_message
                    list_prior_chat_boxes[pick]['status'] = "unseen"
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(pick))
                    data_update = {"num_phone_zalo": num_phone_zalo,
                                   "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)

                return result


def api_update_list_mems_one_group(data, on_chat=False, update=False):
    new_id = data['num_phone_zalo']
    name_ntd = data['name_ntd']
    gvars.list_socket_call.append("get_list_mems_one_group")
    num_phone_zalo = new_id
    num_phone_ntd = None

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']

    try:
        d = gvars.u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối ", id_device)
        gvars.device_connect[id_device] = False
        return False
    if (num_phone_zalo in gvars.dict_status_zalo.keys()):
        if gvars.dict_status_zalo[num_phone_zalo] != '' or gvars.dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if doc['num_phone_zalo'] not in gvars.dict_status_zalo.keys():
                        gvars.dict_status_zalo[doc['num_phone_zalo']] = ""
                    if gvars.dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", gvars.dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":gvars.dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:

                gvars.dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                list_friend = document['list_friend']
                list_group = document['list_group']
                # if 'list_prior_chat_boxes' not in document.keys():
                #    document['list_prior_chat_boxes'] = []
                # list_prior_chat_boxes = document['list_prior_chat_boxes']
                # check_pvp_or_gr = ""
                result = []
                try:
                    if not on_chat:
                        d.app_start("com.zing.zalo", stop=True)
                        gvars.eventlet.sleep(1.0)
                        if num_phone_ntd != None:
                            data_ntd = num_phone_ntd
                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            gvars.eventlet.sleep(1.0)
                            d(resourceId="com.zing.zalo:id/btn_search_result").click()
                            gvars.eventlet.sleep(1.0)
                            check_pvp_or_gr = "pvp"
                            if d(textContains="Đóng").exists:
                                d(textContains="Đóng").click()
                                gvars.eventlet.sleep(0.5)
                            data_ntd = d(
                                resourceId="com.zing.zalo:id/action_bar_title").get_text()

                        else:
                            data_ntd = name_ntd
                            d(text="Tìm kiếm").click()
                            gvars.eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            gvars.eventlet.sleep(1.0)
                            elements = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            if elements:
                                elements[0].click()
                            gvars.eventlet.sleep(1.0)
                            try:
                                if d(textContains="Đóng").exists:
                                    d(textContains="Đóng").click()
                                    gvars.eventlet.sleep(0.5)
                                chat_num = d(
                                    resourceId="com.zing.zalo:id/btn_search_result")
                                chat_num.click()
                            except Exception as e:
                                pass

                    data_ntd = name_ntd
                    check = False
                    pick = -1
                    for id in range(len(list_group)):
                        if list_group[id]['name'] == data_ntd:
                            pick = id
                            check = True
                    if not check:
                        list_group.append(
                            {"name": data_ntd, "time": "", "message": "", "status": "seen", "list_mems": [], "check_mems": False})
                        # time_and_mes = {'time': "",  "message": ""}
                    else:
                        if 'list_mems' not in list_group[pick].keys() or list_group[pick]['list_mems'] == []:
                            list_group[pick]['list_mems'] = []
                    raw_result, check_mems = get_list_members_group_u2(d)
                    result = [r for r in raw_result if r]

                    if len(result) > 0:
                        # if not update:
                        if 'list_mems' not in list_group[pick].keys():
                            list_group[pick]['list_mems'] = []
                        list_group[pick]['list_mems'] = list_group[pick]['list_mems'] + result
                        # else:
                        #    list_group[pick]['list_mems'] = result
                        list_group[pick]['check_mems'] = check_mems
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_group": list_group}
                        update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{gvars.dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    print(e)
                    result = [-1]

                gvars.dict_status_zalo[num_phone_zalo] = ""
                return result
