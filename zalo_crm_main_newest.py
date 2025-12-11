import eventlet
eventlet.monkey_patch()
import sys
from flask_cors import CORS
from flask import Flask, request, jsonify, abort
from uiautomator2 import Direction
from uiautomator2.exceptions import XPathElementNotFoundError
import uiautomator2 as u2
from uiautomator2.exceptions import UiObjectNotFoundError
from threading import Lock
import pymongo
import gridfs
import base64
import traceback
import socket
from io import BytesIO
import psutil
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import multiprocessing
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import Flask, jsonify, request
import threading
import time
import logging
import os
import re
import json
import adbutils
from PIL import Image
import io

load_dotenv()
app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, async_mode='eventlet',
                    max_http_buffer_size=1024 * 1024 * 1024, cors_allowed_origins='*')
# logging.basicConfig(level=logging.DEBUG)

dict_proxy = {"103.82.133.213:13501:sp08-13501:PBTQX": True,
              "103.82.133.213:13519:sp08-13519:IDRMW": True}

dict_status_zalo = {}
dict_status_update_pvp = {}
dict_phone_device = {}
LOG_FILE = "sent_log.txt"
file_lock = Lock()


# đảm bảo biến môi trường cho Python I/O
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# với Python 3.7+:
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    # fallback cho các Python cũ hơn
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace')

dict_device_and_phone = {}
dict_process_id = {}
dict_queue_device = {}

dict_device_and_phone = {
    "R5CW71JT8GT": ["0867956826"],
    "R8YY70F5MKN": [],  # A01
    "TSPNH6GYZLPJBY6X": ['0971335869', '0978025150', '0941295235'],  # A03
    "9PAM7DIFW87DOBEU": ['0869773496', '0395459520', '0988003410'],  # A09
    "EQLNQ8O7EQCQPFXG": [],  # A10
    "YH9TSS7XCMPFZHNR": [],  # A11
    "2926294610DA007N": [],
    "7DXCUKKB6DVWDAQO": ['0385765903', '0963904347', '0969106521'],  # A02
    "7HYP4T4XTS4DXKCY": ['0968082574', '0964876703', '0978722184'],  # A04
    "CQIZKJ8P59AY7DHI": ['0963101851', '0971207216', '0969824937'],  # A08
    "CEIN4X45I7ZHFEFU": ['0973418952', '0971412658', '0961991742'],  # A06
    "8HMN4T9575HAQWLN": ['0978585641', '0982305784', '0973106450'],  # A07
    "UWJJOJLB85SO7LIZ": ['0865772900', '0852039719', '0963563276'],  # A05
    "MJZDFY896TMJBUPN": ['0367614180', '0975629854', '0966049501'],  # A12
    "EY5H9DJNIVNFH6OR": [],  # A13
    "F6NZ5LRKWWGACYQ8": ['0913591672', '0359615945', '0972381905'],  # A14
    "QK8TEMKZMBYHPV6P": ['0984485936', '0968902871', '0985771347'],  # A15
    "IJP78949G69DKNHM": ['0987608429', '0337416995', '0356468640'],  # A16
    "EM4DYTEITCCYJNFU": ['0966117160', '0961963671', '0966578630'],  # A17
    "PN59BMHYPFXCPN8T": ['0966338017', '0383757614', '0982470403'],  # A18
    "Z5LVOF4PRGXGTS9H": ['0988658315', '0338734680', '0967791241'],  # A19
    "R8YY70F81TV": [],  # A21
    "69QGMN8PXWDYPNIF": [],  # A22
    "IZDEGA8TFYXWRK9X": [],  # A23
    "R8YY70HCNRX": [],  # A24
    "R83Y50JZK6A": []  # A25
}

for device_id in dict_device_and_phone.keys():
    for phone_zalo in dict_device_and_phone[device_id]:
        dict_status_zalo[phone_zalo] = ""
        dict_status_update_pvp[phone_zalo] = 0
        dict_phone_device[phone_zalo] = device_id
    dict_process_id[device_id] = 0
    dict_queue_device[device_id] = []

# dict_devices = [dv for dv in dict_device_and_phone.keys()]

dict_devices = []

dict_status_update_data_chat = {}
dict_status_update_list_chat = {}
dict_zalo_online = {}
dict_folder_zalo = {}
Global_update_chat_pvp = {}
last_time = {}
list_auto_tool = []
max_message_per_day = 300
num_message = 0
num_add_friend = 0
image_number = 300
max_add_friend_per_day = 30
device_connect = {}
now_phone_zalo = {}
id_chat = ""
driver = {}

status_auto_send = {}
# Giữ map các driver theo udid để tái sử dụng
drivers = {}
# Thay tất cả time.sleep() bằng eventlet.sleep()
autoit_semaphore = eventlet.semaphore.Semaphore()


def run_start(d: u2.Device):
    # d(resourceId="android:id/home").click()
    btn = d.xpath('//*[@text="Ưu tiên"]')
    if btn.exists:
        print("Có tồn tại ưu tiên")
        return d
    else:
        print("Không tồn tại ưu tiên")
        btn = d(resourceId="com.zing.zalo:id/maintab_message")
        if btn.exists:
            btn.click()
            return d

        btn = d(resourceId="com.zing.zalo:id/action_bar_title")
        if btn.exists:
            d.press("back")
            eventlet.sleep(1.0)
            return d

    d(resourceId="com.android.systemui:id/recent_apps").click()
    d.click(350, 1450)

    try:
        btn = d(text="Zalo")
        if btn.exists:
            btn.click()
    except Exception:
        pass
    return d


def print_usage():
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    print(f"CPU Usage: {cpu_percent}%")
    print(f"RAM Usage: {ram_percent}%")


def create_base_document_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        existing_doc = [d for d in data if d.get(domain) != document[domain]]
        existing_doc.append(document)
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            json.dump(existing_doc, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(e)
        return False


def delete_base_document_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        existing_doc = [d for d in data if d.get(domain) != document[domain]]
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            json.dump(existing_doc, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(e)
        return False


def update_base_document_json(database_name, domain, collection_name, document):
    try:
        #        print(document)
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        for id in range(len(data)):
            #            print(document[domain])
            if data[id][domain] == document[domain]:
                # print(1)
                for key in document.keys():
                    data[id][key] = document[key]
                    # print(document[key])
                break
#        print(data)
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # print(
        #    f"Đã lưu vào database {collection_name}: {data[0]['list_friend'][0]}")
    except Exception as e:
        print(e)
        return False


def get_base_id_zalo_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        # print(data)
        cursor = []
        for d in data:
            check_key = True
            for key in document.keys():
                if d[key] != document[key]:
                    print(d[key])
                    print(document[key])
                    check_key = False
                    break
            if check_key:
                cursor.append(d)
        print(check_key)
        return cursor
    except Exception as e:
        return False


def already_sent(phone_number):
    with file_lock:
        if not os.path.exists(LOG_FILE):
            return False
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return phone_number in f.read()


def log_sent(phone_number):
    with file_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(phone_number + "\n")


def switch_account(d: u2.Device, name, retire=3):

    d.app_start("com.zing.zalo", stop=True)
    # d = run_start(d)
    # d.implicitly_wait(3.0)
    eventlet.sleep(1.0)
    d(resourceId="com.zing.zalo:id/maintab_metab").click()
    eventlet.sleep(1.0)
    d.xpath(
        '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[2]').click()

    eventlet.sleep(1.0)
    d.swipe_ext(Direction.FORWARD)
    eventlet.sleep(1.0)

    d(resourceId="com.zing.zalo:id/itemSwitchAccount").click()

    eventlet.sleep(1.0)
    d.xpath(f"//android.widget.TextView[@text='{name}']").click()
    eventlet.sleep(5)
    d(resourceId="com.zing.zalo:id/btn_chat_gallery_done").click()
    eventlet.sleep(1.5)
    return d


def get_list_friends_u2(d: u2.Device, max_friends: int = 150, scroll_delay: float = 1.0, retire=3, has_update=False, friend_name=[]):
    """
    Lấy toàn bộ bạn bè từ tab Danh bạ trên Zalo Android bằng uiautomator2.
    - d: uiautomator2 Device
    - max_friends: giới hạn tối đa số bạn bè thu thập
    """
    friends = []
    seen = set()
    previous_last = ""
    same_count = 0

    one = time.time()
    d.app_start("com.zing.zalo", stop=True)
    eventlet.sleep(1.0)
    # d.implicitly_wait(3.0)
    two = time.time()
    print(two-one)
    try:
        d(resourceId="com.zing.zalo:id/maintab_contact").click()
        eventlet.sleep(1.0)
    except Exception as e:
        if retire > 0:
            get_list_friends_u2(d, retire=retire-1)
        else:
            return False
    try:
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/layoutTab"]/android.widget.FrameLayout[1]').click()
        eventlet.sleep(1.0)
    except Exception:
        pass

    try:
        if has_update:
            d(resourceId="com.zing.zalo:id/header_page_new_friend").click()
            eventlet.sleep(1.0)
    except Exception as e:
        pass

    try:
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
                if not name or name in seen or name in friend_name or "Tài khoản" in name:
                    continue
                try:

                    items[id].click()
                    eventlet.sleep(1.0)
                    d(resourceId="com.zing.zalo:id/action_bar_title").click()
                    eventlet.sleep(1.0)
                    avatar_b64 = ""
                    try:
                        iv = d(resourceId="com.zing.zalo:id/rounded_avatar_frame")
                        img = iv.screenshot()
                        max_w, max_h = 200, 200
                        img.thumbnail((max_w, max_h), resample=Image.BILINEAR)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", optimize=True, quality=75)
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")
                    except Exception as e:
                        print(e)

                    bd = ""
                    d.xpath(
                        '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[3]').click()
                    eventlet.sleep(0.5)
                    d(resourceId="com.zing.zalo:id/setting_text_primary",
                      text="Thông tin").click()
                    eventlet.sleep(0.5)
                    dob = d(resourceId="com.zing.zalo:id/tv_dob")
                    bd = dob.get_text()
                    eventlet.sleep(0.5)
                    d.press('back')
                    eventlet.sleep(0.5)
                    d.press('back')
                    eventlet.sleep(0.5)

                    if name not in seen:
                        seen.add(name)
                        friends.append({
                            "name": name,
                            "ava": avatar_b64,
                            "day_of_birth": bd
                        })

                    d(resourceId="android:id/home").click()
                    eventlet.sleep(1.0)

                    d(resourceId="android:id/home").click()
                    eventlet.sleep(1.0)

                except Exception as e:
                    print("Lỗi trong quá trình lấy danh sách bạn bè", e)
                    while not d(resourceId="com.zing.zalo:id/maintab_contact").exists:
                        d.press('back')
                        eventlet.sleep(1.0)

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
            eventlet.sleep(scroll_delay)
    except Exception as e:
        print(e)
    return friends


def get_list_groups_u2(d: u2.Device, max_groups: int = 50, scroll_delay: float = 1.0, retire=3):
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
        eventlet.sleep(1.0)
    except (UiObjectNotFoundError, TimeoutError) as e:
        if retire > 0:
            get_list_groups_u2(d, retire=retire-1)
        else:
            return False

    # 2) Chuyển sang phần Nhóm
    try:
        d(resourceId="com.zing.zalo:id/tv_groups").click()
        eventlet.sleep(1)
    except (UiObjectNotFoundError, TimeoutError) as e:
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
            groups.append({
                "name": name,
                "time": time_str,
                "message": message
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
        eventlet.sleep(scroll_delay)

    return groups


def get_list_invite_friends_u2(d: u2.Device, max_friends: int = 100, scroll_delay: float = 1.0, retire=3):
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
        eventlet.sleep(1.0)
    except (UiObjectNotFoundError, TimeoutError) as e:
        if retire > 0:
            get_list_invite_friends_u2(d, retire=retire-1)
        else:
            return False
    try:
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/layoutTab"]/android.widget.FrameLayout[1]').click()
        eventlet.sleep(1.0)
    except Exception:
        pass
    try:
        d(resourceId="com.zing.zalo:id/suggest_friend_request").click()
        eventlet.sleep(1.0)
        d.xpath("//android.widget.TextView[@text='XEM THÊM']").click()
        eventlet.sleep(1.0)
    except (UiObjectNotFoundError, TimeoutError) as e:
        if retire > 0:
            get_list_invite_friends_u2(d, retire=retire-1)
        else:
            return False
    # 2) Lặp scroll & thu thập
    while len(invite_friends) < max_friends:
        # 2.1 Lấy tất cả ô contact invite
        items = d.xpath(
            "//*[@resource-id='com.zing.zalo:id/info_contact_row']").all()
        print(len(items))
        id = 1
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
            print(name_text)
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
                img = iv.screenshot()  # PIL.Image
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                avatar_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            except Exception:
                avatar_b64 = None

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

            print(f"{last_raw.text}-Thật không vậy")
            print(f"{previous_last}-Sao thế hả")
            if last_raw.text == previous_last:
                same_count += 1
                print(f"{same_count}-Sao thế nhỉ")
                if same_count >= 2:
                    break
            else:
                same_count = 0
                previous_last = last_raw.text

        # 2.2 Swipe để load thêm
        w, h = d.window_size()
        d.swipe(w//2, int(h*0.8), w//2, int(h*0.2), duration=0.8)
        eventlet.sleep(scroll_delay)

    return invite_friends


def get_list_members_group_u2(d: u2.Device, max_scroll: int = 100, scroll_delay: float = 1.0):
    # 1) Click vào cuộc nhóm

    # 2) Lấy tên nhóm từ thanh title
    # name = d(resourceId="com.zing.zalo:id/action_bar_title").get_text() or ""

    # 3) Mở navigation drawer và click "Xem thành viên"
    d(resourceId="com.zing.zalo:id/menu_drawer").click()
    eventlet.sleep(1.0)
    d.xpath(
        "//android.widget.FrameLayout[contains(@text, 'Xem thành viên')]").click()
    eventlet.sleep(1.0)

    # 4) Chuẩn bị lưu kết quả
    list_mems = {}
    previous_last = ""
    same_count = 0
    scrolls = 0
    check_mems = True

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
            parts = raw.split("\n")
            name_member = parts[0]
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
            list_mems[name_member] = role

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
        time.sleep(scroll_delay)

    return list_mems, check_mems


list_socket_call = []


@socketio.on('connect')
def handle_connect():
    list_socket_call.append("connect")
    print(f"Client connected: {request.sid}")
    # while True:
    #     print ("list_socket_call ----", list_socket_call)
    #     eventlet.sleep(2)


@socketio.on('join')
def handle_join(data):
    list_socket_call.append("join")
    global id_chat
    room = data['id_chat']
    id_chat = room
    # global folder_data_zalo
    # folder_data_zalo = data['folder_data_zalo']
    # os.makedirs(os.path.join(folder_data_zalo, 'data'), exist_ok=True)
    join_room(room)
    # print(f"Client {request.sid} joined room {room}")
    # res =  update_port_base_id_chat("C:/Zalo_CRM/Zalo_base", "Zalo_data_login_port",room)
    emit("status_update_list_chat", {"status": "1"}, room=room)
    # print ("update_port_base_id_chat------------------", res )


@socketio.on('leave')
def handle_leave(data):
    list_socket_call.append("leave")
    room = data['id_chat']
    leave_room(room)
    print(f"Client {request.sid} left room {room}")

# @app.route('/api_update_list_friend', methods=['POST', 'GET'])


def api_get_list_friend(data_body, check_get_lf):
    # data_body = request.form
    new_id = data_body['num_phone_zalo']
    # global now_phone_zalo
    # global device_connect
    # now_phone_zalo = new_id
    list_socket_call.append("get_list_friend")
    num_phone_zalo = new_id
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    print(docs)
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    list_friend_old = document['list_friend']
    friend_name = [l['name'] for l in list_friend_old]
    print(id_device)
    one = time.time()
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    two = time.time()
    print(two-one)
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "get_list_friend"
                try:
                    result = get_list_friends_u2(
                        d, max_friends=50, has_update=check_get_lf, friend_name=friend_name)
                    print("Kết quả trả về là ", result)

            # dict_zalo_online[room][id_driver]["list_friend"] = result
            # with open(data_login_path, 'w') as json_file:
            #     json.dump(dict_zalo_online, json_file, indent=4)
                    if check_get_lf:
                        result += list_friend_old
                    data_update = {"list_friend": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                # collection_data_login_path.update_one(result[room][id_driver])
                # print ("danh sach fr :" , result)
                # emit("list_friend", {"num_phone_zalo": num_phone_zalo, "list_friend":result}, room=room)
                # print('list_friend:', result)
                except Exception as e:
                    print("Lỗi xaỷ ra khi cào bb", e)
                    result = list_friend_old
                dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result


# @app.route('/api_update_list_group', methods=['POST', 'GET'])
def api_get_list_group(data_body):
    # data_body = request.form
    new_id = data_body['num_phone_zalo']
    list_socket_call.append("get_list_group")
    # global now_phone_zalo
    # global device_connect
    num_phone_zalo = new_id
    # now_phone_zalo = num_phone_zalo
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    print(id_device)
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "get_list_friend"
                try:
                    result = get_list_groups_u2(d, max_groups=150)
                    data_update = {"list_group": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    result = []
                dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result


# @app.route('/api_update_list_invite_friend', methods=['POST', 'GET'])
def api_get_list_invite_friend(data_body):
    # data_body = request.form
    new_id = data_body['num_phone_zalo']
    # global now_phone_zalo
    # global device_connect
    list_socket_call.append("get_list_invite_friend")
    num_phone_zalo = new_id
    # now_phone_zalo = num_phone_zalo
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    print(id_device)
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "get_list_friend"
                try:
                    result = get_list_invite_friends_u2(d)
                    data_update = {"list_invite_friend": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    result = []
                dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result


@app.route('/api_get_list_friend', methods=['POST', 'GET'])
def get_list_friend_new():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    list_socket_call.append("get_list_friend")
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_friend']
    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_friend": result}), 200


@app.route('/api_get_list_group', methods=['POST', 'GET'])
def get_list_group_new():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    list_socket_call.append("get_list_group")
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    now_phone_zalo[id_device] = num_phone_zalo
    result = document['list_group']
    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_group": result}), 200


@app.route('/api_get_list_invite_friend', methods=['POST', 'GET'])
def get_list_invite_friend_new():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    list_socket_call.append("get_list_group")
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_invite_friend']
    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_invite_friend": result}), 200

'''
Code ngày 7/8/2025
'''
mapping = {
    "T2": 0,  # Monday
    "T3": 1,  # Tuesday
    "T4": 2,
    "T5": 3,
    "T6": 4,
    "T7": 5,
    "CN": 6   # Sunday
}


def get_list_prior_chat_boxes_u2(d: u2.Device, tag_name={}, data_chat_boxes={}, max_chat_boxes: int = 50, scroll_delay: float = 1.0, retire=3, scroll_or_not=True):
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
    if scroll_or_not:
        d.app_start("com.zing.zalo", stop=True)
    # d.implicitly_wait(3.0)
    # Phần khởi động

    try:
        # 3) Lặp scroll & thu thập
        while len(chat_boxes) < max_chat_boxes:
            # lấy tất cả item nhóm đang hiển thị
            if d(text="Xem thêm").exists:
                d(text="Xem thêm").click()
                eventlet.sleep(1.0)
            items = d.xpath("//android.widget.FrameLayout[@text!='']").all()

            #print("?")
            for it in items:
                raw = it.text or ""
                if "Media Box" in raw or "Zalo" in raw or "Tin nhắn từ người lạ" in raw or "ngừng hoạt động" in raw or "vào nhóm và cộng đồng" in raw or "Kết bạn" in raw:
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
                now = datetime.now()
                temp = time_str.replace(" ", "")
                if "phút" in time_str:
                    time_str = time_str.replace("phút", "")
                    time_str = time_str.replace(" ", "")
                    dt_minus_48 = now - timedelta(minutes=int(time_str))
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
                    dt_minus_4h = now - timedelta(hours=4)
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
                    today = date.today()
                    time_str = time_str.replace(" ", "")
                    target = mapping.get(time_str.upper())
                    if target is None:
                        raise ValueError("Không xác định được thứ từ đầu vào.")
                    offset = (today.weekday() - target) % 7
                    result = today - timedelta(days=offset)
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
                    today = date.today()
                    year = today.year
                    time_str += "/" + str(year)

                seen.add(name)
                if name in list(tag_name.keys()):
                    tag = tag_name[name]
                else:
                    tag = ""

                if name in list(data_chat_boxes.keys()):
                    data_chat_box = data_chat_boxes[name]
                else:
                    data_chat_box = []

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
            eventlet.sleep(scroll_delay)
    except Exception as e:
        print(e)
        pass
    return chat_boxes


def get_list_unseen_chat_boxes_u2(d: u2.Device, max_chat_boxes: int = 50, scroll_delay: float = 1.0, retire=3):
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

    eventlet.sleep(1.0)
    d.xpath('//*[@resource-id="com.zing.zalo:id/tab_container_right"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[1]').click()
    eventlet.sleep(1.0)
    d.xpath(
        '//*[@resource-id="com.zing.zalo:id/rv_popover_options"]/android.widget.LinearLayout[1]').click()
    eventlet.sleep(1.0)
    try:
        # 3) Lặp scroll & thu thập
        while len(chat_boxes) < max_chat_boxes:
            # lấy tất cả item nhóm đang hiển thị
            items = d.xpath("//android.widget.FrameLayout[@text!='']").all()

            print("?")
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
                now = datetime.now()
                temp = time_str.replace(" ", "")
                if "phút" in time_str:
                    time_str = time_str.replace("phút", "")
                    time_str = time_str.replace(" ", "")
                    dt_minus_48 = now - timedelta(minutes=int(time_str))
                    hour = dt_minus_48.hour
                    minute = dt_minus_48.minute
                    day = dt_minus_48.day
                    month = dt_minus_48.month
                    year = dt_minus_48.year
                    time_str = f"{hour}:{minute} {day}/{month}/{year}"
                elif "giờ" in time_str:
                    dt_minus_4h = now - timedelta(hours=4)
                    hour = dt_minus_4h.hour
                    minute = dt_minus_4h.minute
                    day = dt_minus_4h.day
                    month = dt_minus_4h.month
                    year = dt_minus_4h.year
                    time_str = f"{hour}:{minute} {day}/{month}/{year}"
                elif "T" in time_str or "CN" in time_str:
                    today = date.today()
                    time_str = time_str.replace(" ", "")
                    target = mapping.get(time_str.upper())
                    if target is None:
                        raise ValueError("Không xác định được thứ từ đầu vào.")
                    offset = (today.weekday() - target) % 7
                    result = today - timedelta(days=offset)
                    day = result.day
                    month = result.month
                    year = result.year
                    print("Ngày của", time_str.upper(),
                          "gần nhất:", result.strftime("%d/%m/%Y"))
                    time_str = f"{day}/{month}/{year}"
                elif len(temp) <= 6:
                    today = date.today()
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
            eventlet.sleep(scroll_delay)
    except Exception as e:
        print(e)
        pass
    return chat_boxes


# @app.route('/api_update_list_prior_chat_boxes', methods=['POST', 'GET'])
def api_update_list_prior_chat_boxes(data_body, tag_name={}, data_chat_boxes={}, max_chat_boxes=1000, scroll_or_not=True):
    # data_body = request.form
    new_id = data_body['num_phone_zalo']
    list_socket_call.append("get_list_prior_chat_boxes")
    num_phone_zalo = new_id
    # global device_connect
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    print(id_device)
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break

                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                if scroll_or_not:
                    dict_status_zalo[num_phone_zalo] = "update_list_prior_chat_boxes"
                try:
                    result = get_list_prior_chat_boxes_u2(
                        d, tag_name=tag_name, data_chat_boxes=data_chat_boxes, max_chat_boxes=max_chat_boxes, scroll_or_not=scroll_or_not)
                    if scroll_or_not:
                        data_update = {"list_prior_chat_boxes": result,
                                       "num_phone_zalo": num_phone_zalo}
                        update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    result = []
                dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    if scroll_or_not:
                        result = [box['name'] for box in result]
                return result


def api_update_list_unseen_chat_boxes(data):
    # data_body = request.form
    new_id = data['num_phone_zalo']
    list_socket_call.append("update_list_unseen_chat_boxes")
    num_phone_zalo = new_id
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']
    print(id_device)
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            return False
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "update_list_unseen_chat_boxes"
                try:
                    result = get_list_unseen_chat_boxes_u2(
                        d, max_chat_boxes=50)
                    unseen_boxes = [box['name'] for box in result]
                    data_update = {"list_unseen_chat_boxes": result,
                                   "num_phone_zalo": num_phone_zalo}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                    try:
                        #        print(document)
                        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}.json', 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        for id in range(len(data)):
                            #            print(document[domain])
                            if data[id]['num_phone_zalo'] == num_phone_zalo:
                                for it in range(len(data[id]['list_prior_chat_boxes'])):
                                    if data[id]['list_prior_chat_boxes'][it]['name'] in unseen_boxes:
                                        data[id]['list_prior_chat_boxes'][it]['status'] = "unseen"
#        print(data)
                        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                            print(
                                f"Đã lưu vào database Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}: {data[0]['list_friend'][0]}")
                    except Exception as e:
                        print(e)
                        return False

                except Exception as e:
                    result = []
                dict_status_zalo[num_phone_zalo] = ""
                if len(result) > 0:
                    result = [box['name'] for box in result]
                return result


@app.route('/api_get_list_prior_chat_boxes', methods=['POST', 'GET'])
def get_list_prior_chat_boxes_new():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    list_socket_call.append("get_list_prior_chat_boxes")
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})

    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)

    # docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    list_friend = document['list_friend']
    friend = [fr['name'] for fr in list_friend]
    result = document['list_prior_chat_boxes']
    for id in range(len(result)):
        # result[id]['ava'] = ""
        for it in range(len(friend)):
            if result[id]['name'] == friend[it]:
                result[id]['ava'] = list_friend[it]['ava']
                break
    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_prior_chat_boxes": result}), 200


@app.route('/api_click_tag', methods=['POST', 'GET'])
def get_click_tag():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    tag = data_body.get('tag')
    name_ntd = data_body.get('name_ntd')
    list_socket_call.append("click_tag")
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
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
                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
            break
    return jsonify({"status": "Đã click tag thành công"}), 200


@app.route('/api_get_list_unseen_chat_boxes', methods=['POST', 'GET'])
def get_list_unseen_chat_boxes_new():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    num_phone_zalo = new_id
    # global now_phone_zalo
    # now_phone_zalo = new_id
    list_socket_call.append("get_list_unseen_chat_boxes")
    #print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    result = document['list_unseen_chat_boxes']
    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": user_name, "list_unseen_chat_boxes": result}), 200


@socketio.on('open_chat_pvp')
def handle_chat_pvp(data):
    list_socket_call.append("open_chat_pvp")
    room = data['id_chat']
    num_phone_zalo = data['num_phone_zalo']
    num_send_phone_zalo = data['num_send_phone_zalo']
    name = data['name']
#    ava = data['ava']
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        #print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']

    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1
        dict_status_zalo[num_phone_zalo] = "handle_chat_pvp"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            current_phone = ""
            for it in docs:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    break
            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                    eventlet.sleep(0.2)
                d = u2.connect(id_device)
                d = switch_account(d, user_name)
                if current_phone != "":
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                        "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})
            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return False
                # dict_status_zalo[num_phone_zalo] = "handle_chat_pvp"
        try:
            d = u2.connect(id_device)
            # global device_connect
            device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            emit("busy", {
                "status": dict_status_zalo[num_phone_zalo], 'name_ntd': name}, room=room)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return False
        try:
            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                device_status = json.load(f)
            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    json.dump(device_status, f, indent=4)
                eventlet.sleep(0.2)
                d.app_start("com.zing.zalo", stop=True)
                # eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    eventlet.sleep(0.05)
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            emit("busy", {
                "status": dict_status_zalo[num_phone_zalo], 'name_ntd': name}, room=room)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return False

        try:

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
                            eventlet.sleep(0.1)
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
                                try:
                                    d.xpath(
                                        '//*[@text="Zalo"]').click()
                                    while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                        eventlet.sleep(0.05)
                                except Exception:
                                    pass
                            else:
                                d.press("back")
                                eventlet.sleep(0.1)
                        # d.app_start("com.zing.zalo", stop=True)
                        # d = run_start(d)
                        try:

                            d(text="Tìm kiếm").click()
                            eventlet.sleep(0.1)
                            d.send_keys(
                                f"{num_send_phone_zalo}", clear=True)
                        except Exception as e:
                            print(e)
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
                            emit("receive_chat_view_status", {
                                 "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False

                        try:
                            chat_num = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            chat_num.click()

                        except Exception:
                            emit("receive_chat_view_status", {
                                 "status": "Số điện thoại chưa tạo tài khoản zalo", "name_ntd": name}, room=room)
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                eventlet.sleep(0.1)
                        except Exception:
                            pass

                    try:
                        name_ntd = d(
                            resourceId="com.zing.zalo:id/action_bar_title").get_text()
                    except Exception as e:
                        print(e)
                        dict_status_zalo[num_message] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_chat_view_status", {
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
                    if not check:
                        list_prior_chat_boxes.append(
                            {"name": name_ntd, "phone": num_send_phone_zalo, "time": "", "message": "", "status": "seen", "friend_or_not": "no", "data_chat_box": []})
                    data_update = {"num_phone_zalo": num_phone_zalo,
                                   "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name_ntd:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'
                                data_update = {"num_phone_zalo": num_phone_zalo,
                                               "list_prior_chat_boxes": list_prior_chat_boxes}
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                            break
                join_room(room)
                # emit("receive_chat_view_status",{"status":"Cuộc hội thoại bắt đầu", "name_ntd": name_ntd}, room=room)
                if not already_sent(num_send_phone_zalo):
                    log_sent(num_send_phone_zalo)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                print("Cuộc hội thoại bắt đầu chưa")
                emit("receive_chat_view_status", {
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
                        #    eventlet.sleep(0.1)
                        while not d.xpath('//*[@text="Ưu tiên"]').exists:
                            d.press("back")
                            eventlet.sleep(0.1)
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
                                try:
                                    d.xpath(
                                        '//*[@text="Zalo"]').click()
                                    while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                        eventlet.sleep(0.05)
                                except Exception:
                                    pass
                            else:
                                d.press("back")
                                eventlet.sleep(0.1)
                        # d.app_start("com.zing.zalo", stop=True)
                        # d = run_start(d)
                        #print("vào else à")
                        try:
                            d(text="Tìm kiếm").click()
                            eventlet.sleep(0.1)
                        except Exception as e:
                            print(e)
                            dict_status_zalo[num_message] = ""
                            del dict_queue_device[id_device][0]
                            emit("receive_chat_view_status", {
                                 "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False
                        # time.sleep(1.0)
                        d.send_keys(f"{name}", clear=True)
                        eventlet.sleep(0.15)

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
                                if lines[0] == name:
                                    print("Có trùng khớp")
                                    item.click()
                                    break
                            eventlet.sleep(0.1)
                            #print("Nhấn được chat  chưa")
                        except Exception:
                            emit("receive status", {
                                 "status": "Tài khoản không tồn tại"}, room=room)
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
                            print("Có lỗi à cậu")
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                eventlet.sleep(0.1)
                        except Exception:
                            print("Lỗi có ở đây không")
                            pass

                    #print('ở đây thì sao')
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
                            {"name": name_ntd, "phone": "", "time": "", "message": "", "status": "seen",  "friend_or_not": friend_or_not, "data_chat_box": []})
                    if not check or check_seen or check_add_friend:
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_prior_chat_boxes": list_prior_chat_boxes}
                        update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'
                                data_update = {"num_phone_zalo": num_phone_zalo,
                                               "list_prior_chat_boxes": list_prior_chat_boxes}
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                            break

                join_room(room)
                # emit("receive status",{"status":"Cuộc hội thoại bắt đầu"}, room=room)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                print("Cuộc hội thoại bắt đầu")
                emit("receive_chat_view_status", {
                     "status": "Cuộc hội thoại bắt đầu"}, room=room)
        except Exception as e:
            print(e)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]

        dict_status_update_pvp[num_phone_zalo] = 2
        handle_chat_view(d, num_phone_zalo)
        return True

@app.route('/find_new_friend', methods=['POST', 'GET'])
def api_find_new_friend():
    data = request.form
    num_phone_zalo = data.get('num_phone_zalo')
    num_send_phone_zalo = data.get('num_send_phone_zalo')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    #print(num_phone_zalo)
    #print(num_send_phone_zalo)
    one = time.time()
    # name = data.get('name')
#    ava = data['ava']
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        #print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']

    #print("Đã vào được điện thoại này chưa")
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1
        dict_status_zalo[num_phone_zalo] = "find_new_friend"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            current_phone = ""
            for it in docs:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    break
            # if current_phone != "":
            #    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            #                                       "num_phone_zalo": current_phone, "status": False})
            # Hàm switching (chuyển đổi tài khoản)
            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                    eventlet.sleep(0.2)
                d = u2.connect(id_device)
                d = switch_account(d, user_name)
                if current_phone != "":
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                        "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})
            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return jsonify({"status": "Chuyển tài khoản thất bại"})
        try:
            d = u2.connect(id_device)
            # global device_connect
            device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối", id_device)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return jsonify({"status": "Thiết bị đã ngắt kết nối"})

        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)
        try:
            ck_ac = True
            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    json.dump(device_status, f, indent=4)
                eventlet.sleep(0.1)
                ck_ac = False
                d.app_start("com.zing.zalo", stop=True)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    eventlet.sleep(0.05)

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
                        eventlet.sleep(0.1)
            if not on_chat:
                try:
                    while not d.xpath('//*[@text="Ưu tiên"]').exists:
                        if d.xpath('//*[@text="Zalo"]').exists:
                            try:
                                d.xpath(
                                    '//*[@text="Zalo"]').click()
                                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                                    eventlet.sleep(0.05)
                            except Exception:
                                pass
                        else:
                            d.press("back")
                            eventlet.sleep(0.1)

                    d(text="Tìm kiếm").click()
                    eventlet.sleep(0.1)
                # time.sleep(1.0)
                    d.send_keys(f"{num_send_phone_zalo}", clear=True)
                # time.sleep(1.0)
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_message] = ""
                    del dict_queue_device[id_device][0]
                    return jsonify({"status": "Bận rồi ông cháu ơi"})

                try:
                    chat_num = d(
                        resourceId="com.zing.zalo:id/btn_search_result")
                    chat_num.click()
                    # eventlet.sleep(1.0)
                except Exception:
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    return jsonify({"status": "Bận rồi ông cháu ơi"})

                try:
                    if d(resourceId="com.zing.zalo:id/btn_send_message").exists:
                        d(resourceId="com.zing.zalo:id/btn_send_message").click()
                    eventlet.sleep(0.2)
                except Exception:
                    pass

                try:
                    ntd = d(
                        resourceId="com.zing.zalo:id/action_bar_title")
                    name_ntd = ntd.get_text()
                    ntd.click()
                    eventlet.sleep(0.1)

                except Exception as e:
                    print(e)
                    dict_status_zalo[num_message] = ""
                    del dict_queue_device[id_device][0]
                    return jsonify({"status": "Bận rồi ông cháu ơi"})
                try:
                    iv = d(
                        resourceId="com.zing.zalo:id/rounded_avatar_frame")
                    eventlet.sleep(1.0)

                    img = iv.screenshot()
                    max_w, max_h = 200, 200
                    img.thumbnail((max_w, max_h),
                                  resample=Image.BILINEAR)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG",
                             optimize=True, quality=75)
                    avatar_64 = base64.b64encode(
                        buf.getvalue()).decode("ascii")
                except Exception as e:
                    avatar_64 = ""
                d(resourceId="android:id/home").click()
                eventlet.sleep(1.0)
                btn = d(resourceId="com.zing.zalo:id/tv_function_privacy")

                try:

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
                except Exception as e:
                    friend_or_not = "yes"
                    print(e)

                check = False
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name_ntd:
                        list_prior_chat_boxes[id]['phone'] = num_send_phone_zalo
                        list_prior_chat_boxes[id]['status'] = 'seen'
                        list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                        check = True
                        break
                #if not check:
                #    list_prior_chat_boxes.append(
                #        {"name": name_ntd, "phone": num_send_phone_zalo, "ava": avatar_64, "time": "", "friend_or_not": friend_or_not, "message": "", "status": "seen",  "data_chat_box": []})
                if check:
                    data_update = {"num_phone_zalo": num_phone_zalo,
                            "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                if not already_sent(num_send_phone_zalo):
                    log_sent(num_send_phone_zalo)

            else:
                list_friend = document['list_friend']
                for friend in list_friend:
                    if friend['name'] == name_ntd:
                        avatar_64 = friend['ava']
                        break
                friend_or_not = "yes"
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name_ntd:
                        list_prior_chat_boxes[id]['friend_or_not'] = friend_or_not
                        break
                data_update = {"num_phone_zalo": num_phone_zalo,
                               "list_prior_chat_boxes": list_prior_chat_boxes}
                update_base_document_json(
                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
        except Exception as e:
            print(e)

        dict_status_zalo[num_phone_zalo] = ""
        dict_status_update_pvp[num_phone_zalo] = 0
        del dict_queue_device[id_device][0]

        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)
        if device_status['active'] and len(dict_queue_device[id_device]) == 0:
            device_status['active'] = False
            print("Có set về false không")
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                json.dump(device_status, f, indent=4)

        return jsonify({"num_send_phone_zalo": num_send_phone_zalo, "name_ntd": name_ntd, "ava": avatar_64, "friend_or_not": friend_or_not}), 200


@app.route('/switch_account', methods=['POST', 'GET'])
def api_switch_account():
    # print(data)
    # list_socket_call.append("open_chat_pvp")
    #    room = data["id_chat"]
    # room = data['id_chat']
    data = request.form
    num_phone_zalo = data.get('num_phone_zalo')
    num_send_phone_zalo = data.get('num_send_phone_zalo')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    print(num_phone_zalo)
    print(num_send_phone_zalo)
    one = time.time()
    # name = data.get('name')
#    ava = data['ava']
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    now_phone_zalo[id_device] = num_phone_zalo
    user_name = document['name']
    #list_prior_chat_boxes = document['list_prior_chat_boxes']

    print("Đã vào được điện thoại này chưa")
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1
        dict_status_zalo[num_phone_zalo] = "switch_account"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            current_phone = ""
            for it in docs:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    break

            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                    eventlet.sleep(0.2)
                d = u2.connect(id_device)
                d = switch_account(d, user_name)
                if current_phone != "":
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                        "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})
                dict_status_zalo[num_phone_zalo] = ""
                dict_status_update_pvp[num_phone_zalo] = 0
                del dict_queue_device[id_device][0]
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if device_status['active'] and len(dict_queue_device[id_device]) == 0:
                    device_status['active'] = False
                    print("Có set về false không")
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                return jsonify({"status": "Chuyển tài khoản thành công"})

            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                dict_status_zalo[num_phone_zalo] = ""
                dict_status_update_pvp[num_phone_zalo] = 0
                del dict_queue_device[id_device][0]
                if device_status['active'] and len(dict_queue_device[id_device]) == 0:
                    device_status['active'] = False
                return jsonify({"status": "Chuyển tài khoản thất bại"})


def handle_chat_view(d: u2.Device,  num_phone_zalo):
    last_time[num_phone_zalo] = time.time()
    while True:
        time_period = time.time() - last_time[num_phone_zalo]
        if dict_status_update_pvp[num_phone_zalo] == 1:
            break
        if time_period >= 120.0:
            dict_status_update_pvp[num_phone_zalo] = 0
            name_ntd = d(
                resourceId="com.zing.zalo:id/action_bar_title")
            if name_ntd.exists:
                try:
                    while not d.xpath('//*[@text="Ưu tiên"]').exists:
                        d.press("back")
                        eventlet.sleep(0.1)
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_phone_zalo] = ""
            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                device_status = json.load(f)
            if device_status['active']:
                device_status['active'] = False
                print("Có set về false không")
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    json.dump(device_status, f, indent=4)
            break
        eventlet.sleep(2)


'''
Code ngày 12/8/2025
'''


def parse_bounds(bounds):
    """
    Hỗ trợ 2 dạng bounds thường gặp:
     - chuỗi "[x1,y1][x2,y2]"
     - list/tuple [x1, y1, x2, y2] hoặc dict {...}
    Trả về (left, top, right, bottom)
    """
    if isinstance(bounds, str):
        m = re.findall(r'\[(-?\d+),(-?\d+)\]', bounds)
        if len(m) >= 2:
            x1, y1 = map(int, m[0])
            x2, y2 = map(int, m[1])
            return x1, y1, x2, y2
    elif isinstance(bounds, (list, tuple)) and len(bounds) == 4:
        return tuple(bounds)
    elif isinstance(bounds, dict) and 'left' in bounds:
        return bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
    raise ValueError("Unknown bounds format: %r" % (bounds,))


def safe_click(d, cx, cy, unwanted_resid="com.zing.zalo:id/chat_layout_group_topic",
               safe_offset=12, wait_for_gone_timeout=0):
    """
    Click an toàn:
    - Nếu (cx,cy) nằm trong bounds của unwanted_resid -> di chuyển click ra ngoài (lên trên)
      hoặc chờ phần tử biến mất (nếu wait_for_gone_timeout > 0).
    - safe_offset: số pixel dịch ra khỏi phần tử
    - Trả về vị trí thực tế đã click (x,y)
    """
    elm = d(resourceId="com.zing.zalo:id/chatinput_text")
    if elm.exists:
        try:
            print('Có phần tử Nhắn tin')
            bounds = elm.info.get('bounds')
            top, bottom = bounds['top'], bounds['bottom']
            if top <= cy <= bottom:
                cy = top - 12
        except Exception as e:
            print("Đã xảy ra Exception", e)

    elm = d.xpath('//*[@text="Kết bạn"]')
    if elm.exists:
        try:
            print('Có phần tử Kết bạn')
            bounds = elm.info.get('bounds')
            top, bottom = bounds['top'], bounds['bottom']
            if top <= cy <= bottom:
                cy = top - 12
        except Exception as e:
            print("Đã xảy ra Exception", e)

    el = d(resourceId=unwanted_resid)
    if el.exists:
        try:
            bounds = el.info.get('bounds')
            top, bottom = bounds['top'], bounds['bottom']
            print("Có phần tử tin nhắn ghim")
        except Exception:
            print("Đã xảy ra Exception")
            # nếu không lấy được bounds, fallback: không click trực tiếp ở cx,cy
            # (ở đây chúng ta sẽ di chuyển lên 1/3 chiều cao màn hình)
            # w, h = d.window_size()
            alt_x, alt_y = cx, cy
            d.long_click(alt_x, alt_y, duration=1.0)
            return d

        # nếu toạ độ nằm trong vùng cấm
        if top <= cy <= bottom:
            new_x = cx
            new_y = bottom + 5
            d.long_click(new_x, new_y, duration=1.0)
            return d

    # nếu phần tử không tồn tại hoặc không chặn: click bình thường
    d.long_click(cx, cy, duration=1.0)
    return d


def get_data_chat_boxes_u2(d: u2.Device, gr_or_pvp: str, time_and_mes, max_scroll: int = 5, scroll_delay: float = 1.0):
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
        fr = d(resourceId="com.zing.zalo:id/action_bar_title").get_text()
        name_sender = fr
    check = True
    for nm in range(max_scroll + 1):
        # 2) Tìm tất cả message bubble
        items = d.xpath("//android.view.ViewGroup[@text!='']").all()
        num = len(items) - 1
        # Đọc từ dưới lên trên (các tin mới trước)
        for id in range(num+1):
            raw = items[num-id].text or ""

            # print(raw)

            if gr_or_pvp == 'gr':
                if raw in seen and not any(it in raw for it in nope) and raw not in chat_lack_raw:
                    continue

            else:
                if raw in seen:
                    continue

            if "Tin nhắn đã được thu hồi" in raw or "Gọi điện" in raw:
                continue

            print(time_and_mes)
            print(raw)
            check_1 = True
            if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                raw = raw.split('…')[0]
                if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                    check = False
                    check_1 = False
                    break

                bounds = items[num-id].info['bounds']
                width, height = bounds['right'] - \
                    bounds['left'], bounds['bottom'] - bounds['top']
                if height <= 400:
                    continue
            formatted = date.today().strftime("%d/%m/%Y")
            raw = raw.replace("Hôm nay", formatted)

            seen.add(raw)
            # check_1 = True
            lines = [l for l in raw.split("\n") if l.strip()]
            for line in lines:
                if time_and_mes['message'] == line:
                    check = False
                    check_1 = False
                    break
            if not check_1:
                break
            if "[File]" in raw:
                raw = raw.split('…')[0]
                print("Raw mới là", raw)

                if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                    check = False
                    check_1 = False
                    break
            if not check_1:
                break
            print(raw)
            print(len(lines))
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
                            message = '\n'.join(lines[2:])
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
                            message = '\n'.join(lines[1:])
                    check_you_or_fr = 0
                else:
                    time_str = ""
                    if gr_or_pvp == 'gr':
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        cx = bounds['left'] + int(width * 0.075)
                        cy = bounds['top'] + int(width * 0.075)
                        d.click(cx, cy)
                        eventlet.sleep(1.0)
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
                            bounds = btn.info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            cx = bounds['left'] + int(width * 0.075)
                            cy = bounds['top'] + int(width * 0.075)
                            d.click(700, 270)
                            eventlet.sleep(1.0)
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
                now = datetime.now()
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

                formatted = date.today().strftime("%d/%m/%Y")
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
                    eventlet.sleep(1.5)
                    btn = d.xpath('//*[@text="Trả lời"]')
                    if btn.exists:
                        print("Có tồn tại Trả lời")
                        check_you_or_fr = 2
                        if not lack:
                            chat[f'{name_sender}'] = []
                        elm = d(resourceId="android:id/content")
                        bounds = elm.info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        cx = bounds['left'] + int(width * 0.95)
                        cy = bounds['top'] + height * 0.2
                        d.click(cx, cy)
                        eventlet.sleep(1.0)
                        items = d.xpath(
                            "//android.view.ViewGroup[@text!='']").all()
                        elm = d.xpath('//*[@text="Trả lời"]')
                        if elm.exists:
                            print("Có tồn tại Trả lời")
                        while True:
                            elm = d.xpath('//*[@text="Trả lời"]')

                            print("Có tồn tại Trả lời")
                            if elm.exists:
                                cx = bounds['left'] + int(width * 0.96)
                                cy = bounds['top'] + height * 0.25
                                d.click(cx, cy)
                                eventlet.sleep(1)
                                items = d.xpath(
                                    "//android.view.ViewGroup[@text!='']").all()
                            else:
                                break

                    else:
                        print("Không tồn tại Trả lời")
                        check_you_or_fr = 1
                        chat['you'] = []
                        # continue

                if check_you_or_fr == 1:
                    if typ == 'image':
                        iv = items[num-id].screenshot()
                        img = iv.convert("RGB") if hasattr(
                            iv, "convert") else Image.open(io.BytesIO(iv))

                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']

                        left = bounds['left'] + int(width * 0.225)
                        right = bounds['left'] + int(width * 0.95)
                    # top = bounds['top']
                        top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = int(height * 0.92)
                        print(bottom)

                        cropped = img.crop((left, top, right, bottom))

                        cropped.thumbnail((200, 200), resample=Image.BILINEAR)

                        buf = io.BytesIO()
                        cropped.save(buf, format="JPEG",
                                     optimize=True, quality=75)

                        # output_path = "cropped_output.jpg"
                        # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

                        chat['you'].append(
                            {"time": time_str, "type": typ, "data": message, "image_data": avatar_b64})
                    else:
                        chat['you'].append(
                            {"time": time_str, "type": typ, "data": message})
                else:
                    if typ == 'image':
                        iv = items[num-id].screenshot()
                        img = iv.convert("RGB") if hasattr(
                            iv, "convert") else Image.open(io.BytesIO(iv))

                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']

                        left = bounds['left'] + int(width * 0.125)
                        right = bounds['left'] + int(width * 0.85)
                    # top = bounds['top']
                        top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = int(height * 0.92)
                        print(bottom)

                        cropped = img.crop((left, top, right, bottom))

                        cropped.thumbnail((200, 200), resample=Image.BILINEAR)

                        buf = io.BytesIO()
                        cropped.save(buf, format="JPEG",
                                     optimize=True, quality=75)

                        # output_path = "cropped_output.jpg"
                        # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

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
                                d.click(cx, cy)
                                eventlet.sleep(1.0)
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
                                        message = '\n'.join(lines[1:])
                                    if not lack:
                                        chat[f'{name_sender}'] = []
                                    d.click(700, 270)
                                    eventlet.sleep(1.0)
                                    items = d.xpath(
                                        "//android.view.ViewGroup[@text!='']").all()
                                else:
                                    print("Không có người nhắn")
                                    message = '\n'.join(lines)
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
                            d.click(cx, cy)
                            eventlet.sleep(1.0)
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
                                d.click(700, 270)
                                eventlet.sleep(1.0)
                                items = d.xpath(
                                    "//android.view.ViewGroup[@text!='']").all()
                            else:
                                message = '\n'.join(lines)
                                if raw not in chat_lack_raw:
                                    lack = True
                                    chat_lack_raw.append(raw)
                        else:
                            message = '\n'.join(lines)

                    formatted = date.today().strftime("%d/%m/%Y")
                    time_str = time_str.replace("Hôm nay", formatted)
                    if check_you_or_fr == 0 and "Cuộc gọi thoại đi" not in message and "Cuộc gọi thoại đến" not in message and "Tin nhắn đã được thu hồi" not in message:
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        cx = bounds['left'] + int(width * 0.24)
                        cy = bounds['top'] + height * 0.5
                        print("Đã click rồi")
                        # d.long_click(cx, cy, duration=1.0)
                        d = safe_click(d, cx, cy)
                        print(f"Tọa độ là {cx}, {cy}")
                        eventlet.sleep(1.5)
                        btn = d.xpath('//*[@text="Trả lời"]')
                        if btn.exists:
                            print(btn)
                            info = btn.info
                            print(info)

                            print("Có tồn tại Trả lời")
                            check_you_or_fr = 2
                            if not lack:
                                chat[f'{name_sender}'] = []
                            elm = d(resourceId="android:id/content")
                            bounds = elm.info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            cx = bounds['left'] + int(width * 0.95)
                            cy = bounds['top'] + height * 0.2
                            d.click(cx, cy)
                            eventlet.sleep(1.0)
                            items = d.xpath(
                                "//android.view.ViewGroup[@text!='']").all()
                            # elm = d(text="Trả lời")
                            elm = d.xpath('//*[@text="Trả lời"]')
                            if elm.exists:
                                print("Có tồn tại Trả lời")
                            while True:
                                elm = d.xpath('//*[@text="Trả lời"]')
                                print("Có tồn tại Trả lời")
                                if elm.exists:
                                    cx = bounds['left'] + int(width * 0.96)
                                    cy = bounds['top'] + height * 0.25
                                    d.click(cx, cy)
                                    eventlet.sleep(1)
                                    items = d.xpath(
                                        "//android.view.ViewGroup[@text!='']").all()
                                else:
                                    break

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
                                iv, "convert") else Image.open(io.BytesIO(iv))
                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            left = bounds['left'] + int(width * left_rate)
                            right = bounds['left'] + int(width * right_rate)
                        # top = bounds['top']
                            top = 0 + int(height * top_rate)
                        # bottom = bounds['bottom'] - int(height * 0.08)
                            bottom = 0 + int(height * bottom_rate)
                            print(bottom)
                            cropped = img.crop((left, top, right, bottom))
                            cropped.thumbnail(
                                (200, 200), resample=Image.BILINEAR)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG",
                                         optimize=True, quality=75)
                        # output_path = "cropped_output.jpg"
                        # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                            avatar_b64 = base64.b64encode(
                                buf.getvalue()).decode("ascii")

                        else:
                            iv = d(resourceId="com.zing.zalo:id/video_view")
                            img = iv.screenshot()
                            max_w, max_h = 200, 200
                            # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                            img.thumbnail((max_w, max_h),
                                          resample=Image.BILINEAR)
                            buf = io.BytesIO()
                            # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                            img.save(buf, format="JPEG",
                                     optimize=True, quality=75)
                            # Base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                            avatar_b64 = base64.b64encode(
                                buf.getvalue()).decode("ascii")

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
                                iv, "convert") else Image.open(io.BytesIO(iv))
                            bounds = items[num-id].info['bounds']
                            width, height = bounds['right'] - \
                                bounds['left'], bounds['bottom'] - \
                                bounds['top']
                            left = bounds['left'] + int(width * left_rate)
                            right = bounds['left'] + int(width * right_rate)
                        # top = bounds['top']
                            top = 0 + int(height * top_rate)
                        # bottom = bounds['bottom'] - int(height * 0.08)
                            bottom = 0 + int(height * bottom_rate)
                            print(bottom)
                            cropped = img.crop((left, top, right, bottom))
                            cropped.thumbnail(
                                (200, 200), resample=Image.BILINEAR)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG",
                                         optimize=True, quality=75)
                        # output_path = "cropped_output.jpg"
                        # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                            avatar_b64 = base64.b64encode(
                                buf.getvalue()).decode("ascii")

                        else:
                            iv = d(resourceId="com.zing.zalo:id/video_view")
                            img = iv.screenshot()
                            max_w, max_h = 200, 200
                            # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                            img.thumbnail((max_w, max_h),
                                          resample=Image.BILINEAR)
                            buf = io.BytesIO()
                            # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                            img.save(buf, format="JPEG",
                                     optimize=True, quality=75)
                            # Base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                            avatar_b64 = base64.b64encode(
                                buf.getvalue()).decode("ascii")

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
                            now = datetime.now()
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
                        print(len(chat['you']))
                        if len(chat['you']) > 0:
                            print("Không có thật hả")
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
                        print(len(chat[f'{name_sender}']))
                        if len(chat[f'{name_sender}']) > 0:
                            data_chat_box.append(chat)
                            print("không có thật hả")
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

        # Kiểm tra có cần scroll thêm
    #     if nm >= max_scroll:
    #        break
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
        eventlet.sleep(scroll_delay)

    rever_data_chat_box = data_chat_box[::-1]
    for i in range(len(rever_data_chat_box)):
        for key in rever_data_chat_box[i].keys():
            rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]
    print(rever_data_chat_box)
    return rever_data_chat_box


def get_data_chat_boxes_1vs1_u2(d: u2.Device, time_and_mes, max_scroll: int = 5, scroll_delay: float = 1.0):
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
    fr = d(resourceId="com.zing.zalo:id/action_bar_title").get_text()
    name_sender = fr
    chat[f'{name_sender}'] = []

    if True:
        # 2) Tìm tất cả message bubble
        items = d.xpath("//android.view.ViewGroup[@text!='']").all()
        num = len(items) - 1
        # Đọc từ dưới lên trên (các tin mới trước)
        for id in range(num+1):
            raw = items[num-id].text or ""

            if "đã đồng ý kết bạn" in raw:
                check_f_ac = True

            if raw in seen:
                continue

            if "Tin nhắn đã được thu hồi" in raw:
                continue

            # print(time_and_mes)
            # print(raw)
            check_1 = True
            if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                bounds = items[num-id].info['bounds']
                width, height = bounds['right'] - \
                    bounds['left'], bounds['bottom'] - bounds['top']
                # if height <= 400:
                #    continue
            formatted = date.today().strftime("%d/%m/%Y")
            raw = raw.replace("Hôm nay", formatted)
            if "[File]" in raw:
                raw = raw.split('…')[0]
                if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                    print("Raw data có tồn tại")
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
            # print(lines)
            # print(time_and_mes)
            # for line in lines:
            if time_and_mes['message'] in lines:
                if "[Hình ảnh]" not in time_and_mes['message']:
                    print("Có sự trùng khớp không")
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
                    print("wtf sao lại lỗi ở đây")
                    message = "\n".join(numm[:2])

                formatted = date.today().strftime("%d/%m/%Y")
                time_str = time_str.replace("Hôm nay", formatted)
                typ = 'image' if any(
                    ext in message for ext in ('jpg', 'png')) else 'file'

                if typ == 'image':

                    iv = items[num-id].screenshot()
                    img = iv.convert("RGB") if hasattr(
                        iv, "convert") else Image.open(io.BytesIO(iv))

                    bounds = items[num-id].info['bounds']
                    width, height = bounds['right'] - \
                        bounds['left'], bounds['bottom'] - bounds['top']

                    left = bounds['left'] + int(width * 0.125)
                    right = bounds['left'] + int(width * 0.85)
                    # top = bounds['top']
                    top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                    bottom = int(height * 0.92)
                    print(bottom)

                    cropped = img.crop((left, top, right, bottom))

                    cropped.thumbnail((200, 200), resample=Image.BILINEAR)

                    buf = io.BytesIO()
                    cropped.save(buf, format="JPEG", optimize=True, quality=75)

                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                    avatar_b64 = base64.b64encode(
                        buf.getvalue()).decode("ascii")

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

                    formatted = date.today().strftime("%d/%m/%Y")
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
                            iv, "convert") else Image.open(io.BytesIO(iv))
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        left = bounds['left'] + int(width * left_rate)
                        right = bounds['left'] + int(width * right_rate)
                    # top = bounds['top']
                        top = 0 + int(height * top_rate)
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = 0 + int(height * bottom_rate)
                        print(bottom)
                        cropped = img.crop((left, top, right, bottom))
                        cropped.thumbnail((200, 200), resample=Image.BILINEAR)
                        buf = io.BytesIO()
                        cropped.save(buf, format="JPEG",
                                     optimize=True, quality=75)
                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

                    else:
                        iv = d(resourceId="com.zing.zalo:id/video_view")
                        img = iv.screenshot()
                        max_w, max_h = 200, 200
                        # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                        img.thumbnail((max_w, max_h), resample=Image.BILINEAR)
                        buf = io.BytesIO()
                        # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                        img.save(buf, format="JPEG", optimize=True, quality=75)
                        # Base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

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

    if len(chat[f'{name_sender}']) > 0:
        data_chat_box.append(chat)

    rever_data_chat_box = data_chat_box[::-1]
    for i in range(len(rever_data_chat_box)):
        for key in rever_data_chat_box[i].keys():
            rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]
    print(rever_data_chat_box)

    return rever_data_chat_box, lst_time_str, lst_message, check_f_ac


def get_data_chat_boxes_gr_u2(d: u2.Device, time_and_mes, list_mems, max_scroll: int = 5, scroll_delay: float = 1.0):
    """
    Trả về dict chứa hộp chat hiện có trong màn hình chat của Zalo Android.
    - div_child_selector: dict để tìm tab/conversation (ví dụ {'resourceId': '...', 'text': 'Tên bạn'})
    - device_url: đường dẫn để kết nối uiautomator2 (ví dụ '192.168.1.100:5555')
    - max_scroll: số lần swipe để load tin cũ.
    - scroll_delay: thời gian chờ giữa các lần swipe.
    """
    # d = run_start(d)
    print("Thành viên trong nhóm là: ", list_mems)
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

    if True:
        # 2) Tìm tất cả message bubble
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

            # print(time_and_mes)
            # print(raw)
            check_1 = True
            if "[Hình ảnh]" in raw or "[Sticker]" in raw:
                bounds = items[num-id].info['bounds']
                width, height = bounds['right'] - \
                    bounds['left'], bounds['bottom'] - bounds['top']
                #if height <= 400:
                #    continue
            formatted = date.today().strftime("%d/%m/%Y")
            raw = raw.replace("Hôm nay", formatted)
            if "[File]" in raw:
                raw = raw.split('…')[0]
                if time_and_mes['message'] in raw or raw in time_and_mes['message']:
                    print("Raw data có tồn tại")
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
            # print(lines)
            # print(time_and_mes)
            # for line in lines:
            if time_and_mes['message'] in lines:
                if "[Hình ảnh]" not in time_and_mes['message']:
                    print("Có sự trùng khớp không")
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
                    if lines[1] in list_mems.keys():
                        name_sender = lines[1]
                        ck_sender = True
                        message = '\n'.join(lines[2:-1])
                    else:
                        message = '\n'.join(lines[1:-1])

                elif has_time_token(lines[0]):
                    time_str = lines[0]
                    if lines[1] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[2:])
                    else:
                        message = '\n'.join(lines[1:])

                elif has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[0] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:-1])
                    else:
                        message = '\n'.join(lines[:-1])

                else:
                    time_str = ""
                    if lines[0] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:])
                    else:
                        message = '\n'.join(lines)

                numm = message.split('\n')
                if len(numm) > 2:
                    print("wtf sao lại lỗi ở đây")
                    message = "\n".join(numm[:2])

                formatted = date.today().strftime("%d/%m/%Y")
                time_str = time_str.replace("Hôm nay", formatted)
                typ = 'image' if any(
                    ext in message for ext in ('jpg', 'png')) else 'file'

                avatar_b64 = ""

                if typ == 'image':

                    iv = items[num-id].screenshot()
                    img = iv.convert("RGB") if hasattr(
                        iv, "convert") else Image.open(io.BytesIO(iv))

                    bounds = items[num-id].info['bounds']
                    width, height = bounds['right'] - \
                        bounds['left'], bounds['bottom'] - bounds['top']

                    left = bounds['left'] + int(width * 0.125)
                    right = bounds['left'] + int(width * 0.85)
                    # top = bounds['top']
                    top = 0
                    # bottom = bounds['bottom'] - int(height * 0.08)
                    bottom = int(height * 0.92)
                    print(bottom)

                    cropped = img.crop((left, top, right, bottom))

                    cropped.thumbnail((200, 200), resample=Image.BILINEAR)

                    buf = io.BytesIO()
                    cropped.save(buf, format="JPEG", optimize=True, quality=75)

                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                    avatar_b64 = base64.b64encode(
                        buf.getvalue()).decode("ascii")

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
                    if lines[1] in list_mems.keys():
                        name_sender = lines[1]
                        ck_sender = True
                        message = '\n'.join(lines[2:-1])
                    else:
                        message = '\n'.join(lines[1:-1])

                elif has_time_token(lines[0]):
                    time_str = lines[0]
                    if lines[1] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[2:])
                    else:
                        message = '\n'.join(lines[1:])

                elif has_time_token(lines[-1]):
                    time_str = lines[-1]
                    if lines[0] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:-1])
                    else:
                        message = '\n'.join(lines[:-1])

                else:
                    time_str = ""
                    if lines[0] in list_mems.keys():
                        name_sender = lines[0]
                        ck_sender = True
                        message = '\n'.join(lines[1:])
                    else:
                        message = '\n'.join(lines)

                    formatted = date.today().strftime("%d/%m/%Y")
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
                            iv, "convert") else Image.open(io.BytesIO(iv))
                        bounds = items[num-id].info['bounds']
                        width, height = bounds['right'] - \
                            bounds['left'], bounds['bottom'] - bounds['top']
                        left = bounds['left'] + int(width * left_rate)
                        right = bounds['left'] + int(width * right_rate)
                    # top = bounds['top']
                        top = 0 + int(height * top_rate)
                    # bottom = bounds['bottom'] - int(height * 0.08)
                        bottom = 0 + int(height * bottom_rate)
                        print(bottom)
                        cropped = img.crop((left, top, right, bottom))
                        cropped.thumbnail((200, 200), resample=Image.BILINEAR)
                        buf = io.BytesIO()
                        cropped.save(buf, format="JPEG",
                                     optimize=True, quality=75)
                    # output_path = "cropped_output.jpg"
                    # cropped.convert("RGB").save(output_path, "JPEG", optimize=True, quality=75)
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

                    else:
                        iv = d(resourceId="com.zing.zalo:id/video_view")
                        img = iv.screenshot()
                        max_w, max_h = 200, 200
                        # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                        img.thumbnail((max_w, max_h), resample=Image.BILINEAR)
                        buf = io.BytesIO()
                        # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                        img.save(buf, format="JPEG", optimize=True, quality=75)
                        # Base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                        avatar_b64 = base64.b64encode(
                            buf.getvalue()).decode("ascii")

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

#    if len(chat[f'{name_sender}']) > 0:
#        data_chat_box.append(chat)
    if len(list_data_chat) > 0:
        data_chat_box = list_data_chat
        rever_data_chat_box = data_chat_box[::-1]
    else:
        rever_data_chat_box = data_chat_box[::-1]
        for i in range(len(rever_data_chat_box)):
            for key in rever_data_chat_box[i].keys():
                rever_data_chat_box[i][key] = rever_data_chat_box[i][key][::-1]
    print("Dữ liệu đoan chat thu thập được là: ", rever_data_chat_box)

    return rever_data_chat_box, lst_time_str, lst_message, ck_sender

# @app.route('/api_update_data_one_chat_box', methods=['POST', 'GET'])


def api_update_data_one_chat_box(data, gr_or_pvp="pvp", on_chat=False, update=False):
    # data_body = request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    print(name_ntd)
    list_socket_call.append("get_data_one_box_chat")
    num_phone_zalo = new_id
    num_phone_ntd = None
    # global device_connect
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']

    print(id_device)
    try:
        d = u2.connect(id_device)
        # global device_connect
        device_connect[id_device] = True
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                list_friend = document['list_friend']
                list_group = document['list_group'] = []
                if 'list_prior_chat_boxes' not in document.keys():
                    document['list_prior_chat_boxes'] = []
                list_prior_chat_boxes = document['list_prior_chat_boxes']
                check_pvp_or_gr = ""
                result = []
                try:
                    if not on_chat:
                        d.app_start("com.zing.zalo", stop=True)
                        eventlet.sleep(1.0)
                        if num_phone_ntd != None:
                            data_ntd = num_phone_ntd
                            d(text="Tìm kiếm").click()
                            eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            eventlet.sleep(1.0)
                            d(resourceId="com.zing.zalo:id/btn_search_result").click()
                            eventlet.sleep(1.0)
                            check_pvp_or_gr = "pvp"
                            data_ntd = d(
                                resourceId="com.zing.zalo:id/action_bar_title").get_text()

                        else:
                            data_ntd = name_ntd
                            d(text="Tìm kiếm").click()
                            eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            print("Sao lại in hai lần")
                            eventlet.sleep(1.0)
                            '''
                            elements = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            if elements:
                                elements[0].click()
                            eventlet.sleep(1.0)
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
                                # print(chat_num.get_text())
                                # chat_num.click()
                                eventlet.sleep(1.0)
                            except Exception as e:
                                print(Ellipsis)
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
                            {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": []})
                        time_and_mes = {'time': "",  "message": ""}
                    else:
                        if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == []:
                            list_prior_chat_boxes[pick]['data_chat_box'] = []
                            time_and_mes = {'time': "", "message": ""}
                        else:
                            last_data = list_prior_chat_boxes[pick]['data_chat_box'][-1]
                            last_data_mes = {}
                            for it in last_data.keys():
                                last_data_mes = last_data[it][-1]
                            time_and_mes = {
                                "time": last_data_mes['time'], "message": last_data_mes['data']}
                    raw_result = get_data_chat_boxes_u2(
                        d, gr_or_pvp, time_and_mes)
                    result = [r for r in raw_result if r]
                    '''
                if check_pvp_or_gr == "pvp":
                   for  id in range(len(list_prior_chat_boxes)):
                       if list_prior_chat_boxes[id]['name'] == data_ntd:
                           list_prior_chat_boxes[id]['data_chat_box'] = result
                   data_update = {"num_phone_zalo" : num_phone_zalo, "list_prior_chat_boxes": list_prior_chat_boxes}
                else:
                   for id in range(len(list_prior_chat_boxes)):
                       if list_prior_chat_boxes[id]['name'] == data_ntd:
                           list_prior_chat_boxes[id]['data_chat_box'] = result
                   data_update = {"num_phone_zalo" : num_phone_zalo, "list_prior_chat_boxes": list_prior_chat_boxes}
                 '''
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == data_ntd and len(result) > 0:
                            # if not update:
                            list_prior_chat_boxes[id]['data_chat_box'] = list_prior_chat_boxes[id]['data_chat_box'] + result
                            # else:
                            #    list_prior_chat_boxes[id]['data_chat_box'] = result
                            data_update = {"num_phone_zalo": num_phone_zalo,
                                           "list_prior_chat_boxes": list_prior_chat_boxes}
                            if len(result) > 0:
                                update_base_document_json(
                                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                            break
                except Exception as e:
                    print(e)
                dict_status_zalo[num_phone_zalo] = ""
                return result


def api_update_data_1vs1_chat_box(d: u2.Device, data, document):

    # data_body = request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    print(name_ntd)
    num_phone_zalo = new_id
    print(num_phone_zalo)
    user_name = document['name']
    id_device = document['id_device']
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '':
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:

                # dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
                if 'list_prior_chat_boxes' not in document.keys():
                    document['list_prior_chat_boxes'] = []
                list_prior_chat_boxes = document['list_prior_chat_boxes']
                list_friend = document['list_friend']
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
                        {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": []})
                    time_and_mes = {'time': "",  "message": ""}
                else:
                    print("Hả thật vậy sao")
                    if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == []:

                        list_prior_chat_boxes[pick]['data_chat_box'] = []
                        time_and_mes = {'time': "", "message": ""}
                        print("Thôi xong rơi vào đây rồi")

                    else:
                        # print(list_prior_chat_boxes[pick])
                        last_data = list_prior_chat_boxes[pick]['data_chat_box'][-1]
                        last_data_mes = {}
                        # print(last_data.keys())
                        # print(last_data)
                        for it in last_data.keys():
                            last_data_mes = last_data[it][-1]
                        print("Oke luôn")
                        # print(last_data_mes)
                        time_and_mes = {
                            "time": last_data_mes['time'], "message": last_data_mes['data']}
                raw_result, lst_time_str, lst_message, check_f_ac = get_data_chat_boxes_1vs1_u2(
                    d, time_and_mes)
                result = [r for r in raw_result if r]
                # retr = result

                if len(result) > 0:
                    list_prior_chat_boxes[pick]['data_chat_box'] = list_prior_chat_boxes[pick]['data_chat_box'] + result
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
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                    # retr =  {"result": result}
                # dict_status_zalo[num_phone_zalo] = ""
                # print(result)
                return result


def api_update_data_gr_chat_box(d: u2.Device, data, document):
    # data_body = request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    print(name_ntd)
    num_phone_zalo = new_id
    print(num_phone_zalo)
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
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '':
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:

                # dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
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
                        {"name": data_ntd, "time": "", "message": "", "status": "seen", "tag": "", "data_chat_box": []})
                    time_and_mes = {'time': "",  "message": ""}
                else:
                    print("Hả thật vậy sao")
                    print("Đoạn chat hiện tại", type(
                        list_prior_chat_boxes[pick]))
                    if 'data_chat_box' not in list_prior_chat_boxes[pick].keys() or list_prior_chat_boxes[pick]['data_chat_box'] == []:
                        print(list_prior_chat_boxes[pick].keys())
                        print(list_prior_chat_boxes[pick]['data_chat_box'])
                        print(list_prior_chat_boxes[pick])
                        print("tên nhà tuyển dụng là",
                              list_prior_chat_boxes[pick]['name'])
                        list_prior_chat_boxes[pick]['data_chat_box'] = []
                        time_and_mes = {'time': "", "message": ""}
                        print("Thôi xong rơi vào đây rồi")

                    else:
                        # print(list_prior_chat_boxes[pick])
                        last_data = list_prior_chat_boxes[pick]['data_chat_box'][-1]
                        last_data_mes = {}
                        # print(last_data.keys())
                        # print(last_data)
                        for it in last_data.keys():
                            last_data_mes = last_data[it][-1]
                        print("Oke luôn")
                        print(last_data_mes)
                        time_and_mes = {
                            "time": last_data_mes['time'], "message": last_data_mes['data']}
                raw_result, lst_time_str, lst_message, ck_sender = get_data_chat_boxes_gr_u2(
                    d, time_and_mes, list_mems)
                result = [r for r in raw_result if r]
                # retr = result

                if len(result) > 0:
                    if ck_sender:
                        for res in result:
                            list_prior_chat_boxes[pick]['data_chat_box'].append(
                                res)
                    else:
                        for k in list_prior_chat_boxes[pick]['data_chat_box'][-1].keys():
                            for res in result:
                                list_prior_chat_boxes[pick]['data_chat_box'][-1][k].append(res)

                    list_prior_chat_boxes[pick]['time'] = lst_time_str
                    list_prior_chat_boxes[pick]['message'] = lst_message
                    list_prior_chat_boxes[pick]['status'] = "unseen"
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(pick))
                    data_update = {"num_phone_zalo": num_phone_zalo,
                                   "list_prior_chat_boxes": list_prior_chat_boxes}
                    update_base_document_json(
                        "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                    # retr =  {"result": result}
                # dict_status_zalo[num_phone_zalo] = ""
                # print(result)
                return result


def api_update_list_mems_one_group(data, on_chat=False, update=False):
    # data_body = request.form
    new_id = data['num_phone_zalo']
    # num_phone_ntd = data_body.get('num_phone_ntd')
    name_ntd = data['name_ntd']
    # global device_connect
    print(name_ntd)
    list_socket_call.append("get_list_mems_one_group")
    num_phone_zalo = new_id
    num_phone_ntd = None
    print(num_phone_zalo)

    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    user_name = document['name']

    print(id_device)
    try:
        d = u2.connect(id_device)
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        print("Đến đây chưa")
        if dict_status_zalo[num_phone_zalo] != '' or dict_status_update_pvp[num_phone_zalo] != 0:
            print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
            # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
            return False
        else:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            check_busy = False
            for doc in docs:
                if doc['num_phone_zalo'] != "":
                    if dict_status_zalo[doc['num_phone_zalo']] != "":
                        check_busy = True
                        break
            if check_busy:
                print("bận rồi !!!", dict_status_zalo[num_phone_zalo])
                # emit("busy",{"status":dict_status_zalo[num_phone_zalo]},room=room)
                return False
            else:
                one = time.time()
                doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                            "num_phone_zalo": num_phone_zalo})[0]
                two = time.time()
                print(two-one)
                if not doc['status']:
                    docs = get_base_id_zalo_json(
                        "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
                    current_phone = ""
                    for it in docs:
                        if it['status']:
                            current_phone = it['num_phone_zalo']
                            break
                    try:
                        d = switch_account(d, user_name)
                        if current_phone != "":
                            status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                "num_phone_zalo": current_phone, "status": False})
                        status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                            "num_phone_zalo": num_phone_zalo, "status": True})
                    except Exception as e:
                        print("Chuyển tài khoản thất bại", id_device)
                        return False
                dict_status_zalo[num_phone_zalo] = "get_data_one_box_chat"
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
                        eventlet.sleep(1.0)
                        if num_phone_ntd != None:
                            data_ntd = num_phone_ntd
                            d(text="Tìm kiếm").click()
                            eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            eventlet.sleep(1.0)
                            d(resourceId="com.zing.zalo:id/btn_search_result").click()
                            eventlet.sleep(1.0)
                            check_pvp_or_gr = "pvp"
                            data_ntd = d(
                                resourceId="com.zing.zalo:id/action_bar_title").get_text()

                        else:
                            data_ntd = name_ntd
                            d(text="Tìm kiếm").click()
                            eventlet.sleep(1.0)
                            d.send_keys(data_ntd, clear=True)
                            # print("Sao lại in hai lần")
                            eventlet.sleep(1.0)
                            elements = d(
                                resourceId="com.zing.zalo:id/btn_search_result")
                            if elements:
                                elements[0].click()
                            eventlet.sleep(1.0)
                            try:
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
                    if not check or update:
                        list_group.append(
                            {"name": data_ntd, "time": "", "message": "", "status": "seen", "list_mems": [], "check_mems": False})
                        # time_and_mes = {'time': "",  "message": ""}
                    else:
                        if 'list_mems' not in list_group[pick].keys() or list_group[pick]['list_mems'] == []:
                            list_group[pick]['list_mems'] = []
                            time_and_mes = {'time': "", "message": ""}
                    raw_result, check_mems = get_list_members_group_u2(d)
                    result = [r for r in raw_result if r]

                # for id in range(len(list_group)):
                    if list_group[pick]['name'] == data_ntd and len(result) > 0:
                        # if not update:
                        list_group[pick]['list_mems'] = list_group[pick]['list_mems'] + result
                        # else:
                        #    list_group[pick]['list_mems'] = result
                        list_group[pick]['check_mems'] = check_mems
                        data_update = {"num_phone_zalo": num_phone_zalo,
                                       "list_group": list_group}
                        if len(result) > 0:
                            update_base_document_json(
                                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
                except Exception as e:
                    print(e)

                dict_status_zalo[num_phone_zalo] = ""
                return result


@app.route('/api_get_data_one_chat_box', methods=['POST', 'GET'])
def get_data_one_chat_box():
    data_body = request.form
    new_id = data_body.get('num_phone_zalo')
    # global now_phone_zalo
    # now_phone_zalo = new_id
    name_ntd = data_body.get('name_ntd')
    # num_send_phone_zalo = data_body.get('num_send_phone_zalo')
    num_phone_zalo = new_id
    list_socket_call.append("get_list_prior_chat_boxes")
    print(num_phone_zalo)
    result = []
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
# docs giờ là một list chứa mọi document tìm được
    # id_device = document['id_device']
    # user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    for id in list_prior_chat_boxes:
        if id['name'] == name_ntd:
            if 'data_chat_box' not in id.keys():
                id['data_chat_box'] = []
            result = id['data_chat_box']
            break
        if "phone" in id.keys():
            if id['phone'] == name_ntd:
                name_ntd = id['name']
                if 'data_chat_box' not in id.keys():
                    id['data_chat_box'] = []
                result = id['data_chat_box']
                break

    return jsonify({"num_phone_zalo": num_phone_zalo, "user_name": name_ntd, "data_chat_box": result}), 200


@socketio.on('socket_get_data_one_chat_box')
def get_data_one_chat_box(data):
    new_id = data['num_phone_zalo']
    name_ntd = data['name_ntd']
    room = data['id_chat']
    # global now_phone_zalo
    # now_phone_zalo = new_id
    # num_send_phone_zalo = data_body.get('num_send_phone_zalo')
    num_phone_zalo = new_id
    list_socket_call.append("get_list_prior_chat_boxes")
    print(num_phone_zalo)
    result = []
    friend_or_not = "yes"
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
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
                result = id['data_chat_box']
            if 'friend_or_not' not in id.keys():
                friend_or_not = "yes"
            else:
                friend_or_not = id['friend_or_not']
            break
    join_room(room)
    emit("receive_data_one_chat_box", {
         "num_phone_zalo": num_phone_zalo, "user_name": name_ntd, "data_chat_box": result, "friend_or_not": friend_or_not}, room=room)


special_device = ["9PAM7DIFW87DOBEU"]


@socketio.on('send_message_chat_pvp')
def handle_send_message_chat_pvp(data):
    list_socket_call.append("send_message_chat_pvp")
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
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = json.load(f)

#    ava = data['ava']
    dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    # d = u2.connect(id_device)
    for id in range(len(device_status['max_message_per_day'])):
        if num_phone_zalo in device_status['max_message_per_day'][id].keys():
            if device_status['max_message_per_day'][id][num_phone_zalo] <= 0:
                join_room(room)
                emit(
                    "receive status", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
                return False

    if num_message >= max_message_per_day:
        emit(
            "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
        return False
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1

        dict_status_zalo[num_phone_zalo] = "send_message_chat_pvp"
        # with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        #    device_status = json.load(f)
        try:
            try:
                d = u2.connect(id_device)
            except Exception as e:
                print("Thiết bị đã ngắt kết nối")
                emit("busy", {
                    "status": dict_status_zalo[num_phone_zalo], 'name_ntd': name}, room=room)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return False
            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    json.dump(device_status, f, indent=4)
                eventlet.sleep(0.1)
                try:
                    d.app_start("com.zing.zalo", stop=True)
                    while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                        eventlet.sleep(0.05)
                except Exception as e:
                    print("Thiết bị đã ngắt kết nối")
                    emit("busy", {
                        "status": dict_status_zalo[num_phone_zalo], 'name_ntd': name}, room=room)
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    return False

                # eventlet.sleep(1.0)
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
                            dict_status_zalo[num_message] = ""
                            del dict_queue_device[id_device][0]
                            emit("receive_chat_view_status", {
                                 "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                            return False

                        d.send_keys(f"{name}", clear=True)
                        eventlet.sleep(0.15)

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
                                if lines[0] == name:
                                    print("Có trùng khớp")
                                    item.click()
                                    break
                            eventlet.sleep(1.0)
                            print("Nhấn được chat  chưa")
                        except Exception:
                            emit("receive status", {
                                 "status": "Tài khoản không tồn tại"}, room=room)
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
                            print("Có lỗi à cậu")
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                eventlet.sleep(1.0)
                        except Exception:
                            print("Lỗi có ở đây không")
                            pass
                except Exception as e:
                    print(e)
                # if d is None:

            if type == 'image':
                avatar = base64.b64decode(image_data)
                with open(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg', 'wb') as f:
                    f.write(avatar)
                print(
                    f"Đã lưu vào thư mục Zalo_base/image{image_number}.jpg")
                d.push(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg',
                       f'/sdcard/Download/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                eventlet.sleep(0.1)
                image_number -= 1
                print("Đã click vào chưa")
                '''
                    if id_device in special_device:
                        try:
                           d(resourceId="com.zing.zalo:id/new_chat_input_btn_show_gallery").click_exists(timeout=3)
                           d.xpath('//*[@resource-id="com.zing.zalo:id/recycler_view"]/android.widget.FrameLayout[2]').click_exists(timeout=3)
                           #d(resourceId="com.zing.zalo:id/new_chat_input_btn_send_media").click_exists(timeout=3)
                           d(resourceId="com.zing.zalo:id/landing_page_layout_send").click_exists(timeout=3)
                        except Exception as e:
                            print(e)
                            dict_status_zalo[num_phone_zalo] = ""
                            emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                            return False 
                    '''
                # if id_device in special_device:

                try:
                  # if id_device not in special_device:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    d.xpath(
                        '//*[@text="Tài liệu"]').click()
                    eventlet.sleep(1)

                    if d.xpath('//*[@text="Gần đây"]').exists:
                        d(description="Hiển thị gốc").click_exists(
                            timeout=3)
                        eventlet.sleep(0.2)
                        td = d.xpath('//*[@text="Tệp đã tải xuống"]')
                        if td.exists:
                            td.click()
                            eventlet.sleep(0.1)
                        else:
                            if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                d(resourceId="android:id/title",
                                  text="Tệp đã tải xuống").click()
                                # eventlet.sleep(0.1)
                            else:
                                d.xpath(
                                    '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                        eventlet.sleep(0.1)
                    click_btn = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                    if click_btn.exists:
                        click_btn.click_exists(timeout=0.1)
                        eventlet.sleep(0.1)
                    btn1 = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                    btn2 = d(
                        resourceId="com.google.android.documentsui:id/item_root")
                    if btn1.exists:
                        btn1.click()
                        eventlet.sleep(0.1)
                    elif btn2.exists:
                        btn2.click()
                        eventlet.sleep(0.1)
                    if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        # pass
                    else:
                        # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                        d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False
            elif type == 'file':
                file_decode = base64.b64decode(file_data)

                with open(f'C:/Zalo_CRM/Zalo_base/{file_name}', 'wb') as f:
                    f.write(file_decode)
                d.push(f'C:/Zalo_CRM/Zalo_base/{file_name}',
                       f'/sdcard/Download/{file_name}')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                eventlet.sleep(0.1)
                # image_number -= 1
                print("Đã click vào chưa")
                try:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    d.xpath(
                        '//*[@text="Tài liệu"]').click()
                    eventlet.sleep(1)

                    if d.xpath('//*[@text="Gần đây"]').exists:
                        d(description="Hiển thị gốc").click_exists(
                            timeout=3)
                        eventlet.sleep(0.2)
                        td = d.xpath('//*[@text="Tệp đã tải xuống"]')
                        if td.exists:
                            td.click()
                            eventlet.sleep(0.1)
                        else:
                            if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                d(resourceId="android:id/title",
                                  text="Tệp đã tải xuống").click()
                                # eventlet.sleep(0.1)
                            else:
                                d.xpath(
                                    '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                        eventlet.sleep(0.1)
                    click_btn = d.xpath(
                        '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                    if click_btn.exists:
                        click_btn.click_exists(timeout=0.1)
                        eventlet.sleep(0.1)
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
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False

            elif type == 'text':

                try:
                    d(resourceId="com.zing.zalo:id/chatinput_text").click()
                    eventlet.sleep(0.1)
                    d.send_keys(message, clear=True)
                    eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False
            elif type == 'card':
                try:
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    eventlet.sleep(0.1)
                    d.xpath('//*[@text="Danh thiếp"]').click()
                    eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/search_input_text").click()
                    eventlet.sleep(0.1)
                    d.send_keys(name_card, clear=True)
                    eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/layoutcontact").click()
                    eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/btn_done_add_item").click()
                    eventlet.sleep(0.1)
                    d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                    eventlet.sleep(0.1)
                except Exception as e:
                    print(e)
                    dict_status_zalo[num_phone_zalo] = ""
                    del dict_queue_device[id_device][0]
                    emit("receive_send_message_status", {
                        "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                    return False

            now = datetime.now()
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
            eventlet.sleep(1.0)
            join_room(room)
            check = False
            # pick = -1
            for id in range(len(list_prior_chat_boxes)):
                if list_prior_chat_boxes[id]['name'] == name:
                    check = True
                    if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                        print("Có khôngs")
                        list_prior_chat_boxes[id]['data_chat_box'] = []
                    if type == 'text':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        list_prior_chat_boxes[id]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "text", "data": message}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'image':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        list_prior_chat_boxes[id]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'file':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        list_prior_chat_boxes[id]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    elif type == 'card':
                        list_prior_chat_boxes[id]['time'] = time_str
                        list_prior_chat_boxes[id]['message'] = message
                        list_prior_chat_boxes[id]['status'] = "seen"
                        list_prior_chat_boxes[id]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "card", "data": f"{name_card}\nGọi điện\nNhắn tin", "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(id))
                    break

                    # pick = id
            if not check:
                data_chat_box = []
                if type == 'text':
                    num = message.split(" ")
                    if num > 10:
                        num = num[:10]
                        message = " ".join(num)
                    list_prior_chat_boxes.append(
                        {"name": name, "time": time_str, "message": message, "status": "seen", "data_chat_box": []})
                    list_prior_chat_boxes[-1]['data_chat_box'].append(
                        {"you": [{'time': time_str, 'type': "text", "data": message}]})
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'image':
                    list_prior_chat_boxes.append(
                        {"name": name, "time": time_str, "message": f"image{image_number+1}.jpg", "status": "seen", "data_chat_box": []})
                    list_prior_chat_boxes[-1]['data_chat_box'].append(
                        {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'file':
                    list_prior_chat_boxes.append(
                        {"name": name, "time": time_str, "message": f"[File]\n{file_name}\n{file_size}", "status": "seen", "data_chat_box": []})
                    list_prior_chat_boxes[-1]['data_chat_box'].append(
                        {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))
                elif type == 'card':
                    list_prior_chat_boxes.append(
                        {"name": name, "time": time_str, "message": message, "status": "seen", "data_chat_box": []})
                    list_prior_chat_boxes[-1]['data_chat_box'].append(
                        {"you": [{'time': time_str, 'type': "card", "data": message, "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                    list_prior_chat_boxes.insert(
                        0, list_prior_chat_boxes.pop(-1))

            data_update = {"num_phone_zalo": num_phone_zalo,
                           "list_prior_chat_boxes": list_prior_chat_boxes}
            update_base_document_json(
                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
            if type == 'card':
                emit("receive status", {
                    "status": "Đã gửi tin nhắn thành công"}, room=room)
            emit('receive_list_prior_chat_box', {
                'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, room=room)
        except Exception as e:
            print(e)
            emit("receive status", {
                "status": "Đã gửi tin nhắn thất bại"}, room=room)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]

            dict_status_update_pvp[num_phone_zalo] = 2
            handle_chat_view(d, num_phone_zalo)
            return False
        num_message += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)

        for id in range(len(device_status['max_message_per_day'])):
            if num_phone_zalo in device_status['max_message_per_day'][id].keys():
                device_status['max_message_per_day'][id][num_phone_zalo] -= 1

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            json.dump(device_status, f, indent=4)

        dict_status_zalo[num_phone_zalo] = ""
        dict_status_update_pvp[num_phone_zalo] = 2
        del dict_queue_device[id_device][0]
        # two = time.time()
        # print(two-one)
        handle_chat_view(d, num_phone_zalo)


@socketio.on('share_message_chat_pvp')
def handle_share_message_chat_pvp(data):
    list_socket_call.append("share_message_chat_pvp")
#    room = data["id_chat"]
    room = data['id_chat']
    #print("helloo every one")
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

    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = json.load(f)

    for id in range(len(device_status['max_message_per_day'])):
        if num_phone_zalo in device_status['max_message_per_day'][id].keys():
            if device_status['max_message_per_day'][id][num_phone_zalo] <= 0:
                emit(
                    "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
                return False

    if num_message >= max_message_per_day:
        emit(
            "limit", {"status": "Đã đạt giới hạn nhắn tin một ngày"}, room=room)
        return False
#    ava = data['ava']
    dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    # d = u2.connect(id_device)
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)
        dict_status_update_pvp[num_phone_zalo] = 1

        dict_status_zalo[num_phone_zalo] = "share_message_chat_pvp"
#                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
#                    device_status = json.load(f)
        try:
            d = u2.connect(id_device)
        except Exception as e:
            print("Thiết bị đã ngắt kết nối")
            emit("busy", {
                "status": dict_status_zalo[num_phone_zalo], 'name_ntd': name}, room=room)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return False
        try:

            if not device_status['active']:
                device_status['active'] = True
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    json.dump(device_status, f, indent=4)
                eventlet.sleep(0.1)
                d.app_start("com.zing.zalo", stop=True)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    eventlet.sleep(0.05)
                # if d is None:
            #print("Mảng có rỗng hay không")
            for name in names:
                #print("con cjdk")
                #print("Đã vào share chưa", name)
                #################################
                on_chat = False
                btn = d(resourceId="com.zing.zalo:id/action_bar_title")
                if btn.exists:
                    current_ntd = btn.get_text()
                    #print(current_ntd)
                    if current_ntd == name:
                        on_chat = True
                    else:
                        try:
                            # d.press("back")
                            # if d(resourceId="com.zing.zalo:id/action_bar_title").exists:
                            #    d.press("back")
                            while not d.xpath('//*[@text="Ưu tiên"]').exists:
                                d.press("back")
                                eventlet.sleep(0.1)
                        except Exception as e:
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
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
                                        eventlet.sleep(1.5)
                                    except Exception:
                                        pass
                                else:
                                    d.press("back")

                            # d.app_start("com.zing.zalo", stop=True)
                            # d = run_start(d)
                            print("vào else à")
                            try:
                                # d(text="Tìm kiếm").click()
                                d(text="Tìm kiếm").click_exists(
                                    timeout=1)
                            except Exception as e:
                                print(e)
                                dict_status_zalo[num_message] = ""
                                del dict_queue_device[id_device][0]
                                emit("receive_chat_view_status", {
                                     "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name}, room=room)
                                return False
                            # time.sleep(1.0)
                            d.send_keys(f"{name}", clear=True)
                            eventlet.sleep(0.15)

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
                                    if lines[0] == name:
                                        print("Có trùng khớp")
                                        item.click()
                                        break
                                eventlet.sleep(1.0)
                                print("Nhấn được chat  chưa")
                            except Exception:
                                emit("receive status", {
                                     "status": "Tài khoản không tồn tại"}, room=room)
                                dict_status_zalo[num_phone_zalo] = ""
                                del dict_queue_device[id_device][0]
                                print("Có lỗi à cậu")
                                return False

                            try:
                                btn = d(
                                    resourceId="com.zing.zalo:id/btn_send_message")
                                if btn.exists:
                                    btn.click()
                                    eventlet.sleep(1.0)
                            except Exception:
                                print("Lỗi có ở đây không")
                                pass
                    except Exception as e:
                        print(e)

                    print('ở đây thì sao')
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
                            {"name": name, "phone": "", "time": "", "message": "", "status": "seen",  "friend_or_not": friend_or_not, "data_chat_box": []})

                else:
                    for id in range(len(list_prior_chat_boxes)):
                        if list_prior_chat_boxes[id]['name'] == name:
                            if list_prior_chat_boxes[id]['status'] == 'unseen':
                                list_prior_chat_boxes[id]['status'] = 'seen'

                            break

                if type == 'image':
                    avatar = base64.b64decode(image_data)
                    with open(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg', 'wb') as f:
                        f.write(avatar)
                    print(
                        f"Đã lưu vào thư mục Zalo_base/image{image_number}.jpg")
                    d.push(f'C:/Zalo_CRM/Zalo_base/image{image_number}.jpg',
                           f'/sdcard/Download/image{image_number}.jpg')
                    # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                    # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                    eventlet.sleep(0.1)
                    image_number -= 1
                    #print("Đã click vào chưa")

                    # if id_device in special_device:

                    try:
                      # if id_device not in special_device:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        d.xpath(
                            '//*[@text="Tài liệu"]').click()
                        eventlet.sleep(1)

                        if d.xpath('//*[@text="Gần đây"]').exists:
                            d(description="Hiển thị gốc").click_exists(
                                timeout=3)
                            eventlet.sleep(0.2)
                            td = d.xpath(
                                '//*[@text="Tệp đã tải xuống"]')
                            if td.exists:
                                td.click()
                                eventlet.sleep(0.1)
                            else:
                                if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                    d(resourceId="android:id/title",
                                      text="Tệp đã tải xuống").click()
                                    # eventlet.sleep(0.1)
                                else:
                                    d.xpath(
                                        '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                            eventlet.sleep(0.1)
                        click_btn = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                        if click_btn.exists:
                            click_btn.click_exists(timeout=0.1)
                            eventlet.sleep(0.1)
                        btn1 = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]')
                        btn2 = d(
                            resourceId="com.google.android.documentsui:id/item_root")
                        if btn1.exists:
                            btn1.click()
                            eventlet.sleep(0.1)
                        elif btn2.exists:
                            btn2.click()
                            eventlet.sleep(0.1)
                        if d(resourceId="com.zing.zalo:id/chatinput_text").exists:
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                            # pass
                        else:
                            # d.xpath('//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]').click_exists(timeout=3)
                            d.xpath(
                                '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[2]').click_exists(timeout=3)
                            eventlet.sleep(0.1)
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        dict_status_zalo[num_phone_zalo] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False
                elif type == 'file':
                    file_decode = base64.b64decode(file_data)

                    with open(f'C:/Zalo_CRM/Zalo_base/{file_name}', 'wb') as f:
                        f.write(file_decode)
                    d.push(f'C:/Zalo_CRM/Zalo_base/{file_name}',
                           f'/sdcard/Download/{file_name}')
                    # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/DCIM/Zalo/image{image_number}.jpg')
                    # d.push('C:/Zalo_CRM/Zalo_base/image.jpg', f'/sdcard/Pictures/Zalo/image{image_number}.jpg')
                    eventlet.sleep(0.1)
                    # image_number -= 1
                    #print("Đã click vào chưa")
                    try:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        d.xpath(
                            '//*[@text="Tài liệu"]').click()
                        eventlet.sleep(1)

                        if d.xpath('//*[@text="Gần đây"]').exists:
                            d(description="Hiển thị gốc").click_exists(
                                timeout=3)
                            eventlet.sleep(0.2)
                            td = d.xpath(
                                '//*[@text="Tệp đã tải xuống"]')
                            if td.exists:
                                td.click()
                                eventlet.sleep(0.1)
                            else:
                                if d(resourceId="android:id/title", text="Tệp đã tải xuống").exists:
                                    d(resourceId="android:id/title",
                                      text="Tệp đã tải xuống").click()
                                    # eventlet.sleep(0.1)
                                else:
                                    d.xpath(
                                        '//*[@resource-id="com.google.android.documentsui:id/roots_list"]/android.widget.LinearLayout[4]').click_exists(timeout=3)
                            eventlet.sleep(0.1)
                        click_btn = d.xpath(
                            '//*[@resource-id="com.google.android.documentsui:id/dir_list"]/androidx.cardview.widget.CardView[1]/androidx.cardview.widget.CardView[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]')
                        if click_btn.exists:
                            click_btn.click_exists(timeout=0.1)
                            eventlet.sleep(0.1)
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
                            eventlet.sleep(0.1)
                            d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click_exists(
                                timeout=1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        dict_status_zalo[num_phone_zalo] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False

                elif type == 'text':

                    try:
                        d(resourceId="com.zing.zalo:id/chatinput_text").click()
                        eventlet.sleep(0.1)
                        d.send_keys(message, clear=True)
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        dict_status_zalo[num_phone_zalo] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)
                        return False
                elif type == 'card':
                    try:
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        eventlet.sleep(0.1)
                        d.xpath('//*[@text="Danh thiếp"]').click()
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/search_input_text").click()
                        eventlet.sleep(0.1)
                        d.send_keys(name_card, clear=True)
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/layoutcontact").click()
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/btn_done_add_item").click()
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_attach").click()
                        eventlet.sleep(0.1)
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        dict_status_zalo[num_phone_zalo] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": message}, room=room)

                now = datetime.now()
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
                eventlet.sleep(1.0)
                join_room(room)
                check = False
                # pick = -1
                for id in range(len(list_prior_chat_boxes)):
                    if list_prior_chat_boxes[id]['name'] == name:
                        check = True
                        if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                            print("Có khôngs")
                            list_prior_chat_boxes[id]['data_chat_box'] = [
                            ]
                        if type == 'text':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            list_prior_chat_boxes[id]['data_chat_box'].append(
                                {"you": [{'time': time_str, 'type': "text", "data": message}]})
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'image':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            list_prior_chat_boxes[id]['data_chat_box'].append(
                                {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'file':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            list_prior_chat_boxes[id]['data_chat_box'].append(
                                {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        elif type == 'card':
                            list_prior_chat_boxes[id]['time'] = time_str
                            list_prior_chat_boxes[id]['message'] = message
                            list_prior_chat_boxes[id]['status'] = "seen"
                            list_prior_chat_boxes[id]['data_chat_box'].append(
                                {"you": [{'time': time_str, 'type': "card", "data": f"{name_card}\nGọi điện\nNhắn tin", "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                            list_prior_chat_boxes.insert(
                                0, list_prior_chat_boxes.pop(id))
                        break

                        # pick = id
                if not check:
                    data_chat_box = []
                    if type == 'text':
                        num = message.split(" ")
                        if num > 10:
                            num = num[:10]
                            message = " ".join(num)
                        list_prior_chat_boxes.append(
                            {"name": name, "time": time_str, "message": message, "status": "seen", "data_chat_box": []})
                        list_prior_chat_boxes[-1]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "text", "data": message}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'image':
                        list_prior_chat_boxes.append(
                            {"name": name, "time": time_str, "message": f"image{image_number+1}.jpg", "status": "seen", "data_chat_box": []})
                        list_prior_chat_boxes[-1]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "image", "data": f"image{image_number+1}.jpg", "image_data": image_data}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'file':
                        list_prior_chat_boxes.append(
                            {"name": name, "time": time_str, "message": f"[File]\n{file_name}\n{file_size}", "status": "seen", "data_chat_box": []})
                        list_prior_chat_boxes[-1]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "file", "data": f"[File]\n{file_name}\n{file_size}", "file_data": file_data}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))
                    elif type == 'card':
                        list_prior_chat_boxes.append(
                            {"name": name, "time": time_str, "message": message, "status": "seen", "data_chat_box": []})
                        list_prior_chat_boxes[-1]['data_chat_box'].append(
                            {"you": [{'time': time_str, 'type': "card", "data": message, "card_data": {"name_card": name_card, "num_phone_card": num_phone_card}}]})
                        list_prior_chat_boxes.insert(
                            0, list_prior_chat_boxes.pop(-1))

                if extra_message != "":
                    try:
                        d(resourceId="com.zing.zalo:id/chatinput_text").click()
                        eventlet.sleep(0.1)
                        d.send_keys(extra_message, clear=True)
                        eventlet.sleep(0.1)
                        d(resourceId="com.zing.zalo:id/new_chat_input_btn_chat_send").click()
                    except Exception as e:
                        print("Lỗi gặp phải là: ", e)
                        dict_status_zalo[num_phone_zalo] = ""
                        del dict_queue_device[id_device][0]
                        emit("receive_send_message_status", {
                            "status": "Gửi tin nhắn thất bại",  "name_ntd": name, "message": extra_message}, room=room)
                        return False
                    now = datetime.now()
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
                    eventlet.sleep(1.0)

                    id = 0
                # for id in range(len(list_prior_chat_boxes)):
                #    if list_prior_chat_boxes[id]['name'] == name:
                #        check = True
                    if 'data_chat_box' not in list_prior_chat_boxes[id].keys():
                        #print("Có khôngs")
                        list_prior_chat_boxes[id]['data_chat_box'] = []

                    list_prior_chat_boxes[id]['time'] = time_str
                    list_prior_chat_boxes[id]['message'] = extra_message
                    list_prior_chat_boxes[id]['status'] = "seen"
                    list_prior_chat_boxes[id]['data_chat_box'].append(
                        {"you": [{'time': time_str, 'type': "text", "data": extra_message}]})

            data_update = {"num_phone_zalo": num_phone_zalo,
                           "list_prior_chat_boxes": list_prior_chat_boxes}
            update_base_document_json(
                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
            if True:
                on_chat = False
                btn = d(resourceId="com.zing.zalo:id/action_bar_title")
                if btn.exists:
                    current_ntd = btn.get_text()
                    #print(current_ntd)
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
                                    eventlet.sleep(1.5)
                                except Exception:
                                    pass
                            else:
                                d.press("back")
                        # d.app_start("com.zing.zalo", stop=True)
                        # d = run_start(d)
                        #print("vào else à")
                        try:
                            # d(text="Tìm kiếm").click()
                            d(text="Tìm kiếm").click()
                        except Exception as e:
                            print(e)
                            dict_status_zalo[num_message] = ""
                            del dict_queue_device[id_device][0]
                            emit("receive_chat_view_status", {
                                 "status": "Mở chat thất bại, hãy thử mở lại", "name_ntd": name_share}, room=room)
                            return False
                        # time.sleep(1.0)
                        d.send_keys(f"{name_share}", clear=True)
                        eventlet.sleep(0.15)

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
                                if lines[0] == name_share:
                                    print("Có trùng khớp")
                                    item.click()
                                    break
                            eventlet.sleep(1.0)
                            #print("Nhấn được chat  chưa")
                        except Exception as e:
                            emit("receive status", {
                                 "status": "Tài khoản không tồn tại"}, room=room)
                            dict_status_zalo[num_phone_zalo] = ""
                            del dict_queue_device[id_device][0]
                            #print("Có lỗi à cậu")
                            print("Lỗi gặp phải là: ", e)
                            return False

                        try:
                            btn = d(
                                resourceId="com.zing.zalo:id/btn_send_message")
                            if btn.exists:
                                btn.click()
                                eventlet.sleep(1.0)
                        except Exception as e:
                            print("Lỗi gặp phải là: ", e)
                            pass

            emit("receive_share_status", {
                "status": "Đã chia sẻ tin nhắn thành công"}, room=room)
            emit('receive_list_prior_chat_box', {
                'user_name': name_share, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, room=room)
        except Exception as e:
            print(e)

            dict_status_zalo[num_phone_zalo] = ""
            dict_status_update_pvp[num_phone_zalo] = 2
            del dict_queue_device[id_device][0]
            handle_chat_view(d, num_phone_zalo)
            return False
        num_message += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)

        for id in range(len(device_status['max_message_per_day'])):
            if num_phone_zalo in device_status['max_message_per_day'][id].keys():
                device_status['max_message_per_day'][id][num_phone_zalo] -= 1
                if extra_message != "":
                    device_status['max_message_per_day'][id][num_phone_zalo] -= 1
        dict_status_zalo[num_phone_zalo] = ""
        dict_status_update_pvp[num_phone_zalo] = 2
        del dict_queue_device[id_device][0]
        # two = time.time()
        # print(two-one)
        handle_chat_view(d, num_phone_zalo)

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            json.dump(device_status, f, indent=4)


@app.route('/api_add_friend_chat_pvp', methods=['POST', 'GET'])
def api_add_friend_chat_pvp():
    data = request.form
    list_socket_call.append("add_friend_chat_pvp")
    num_phone_zalo = data.get('num_phone_zalo')
    name = data.get('name')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_add_friend
    global max_add_friend_per_day
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = json.load(f)

    for id in range(len(device_status['max_add_friend_per_day'])):
        if num_phone_zalo in device_status['max_add_friend_per_day'][id].keys():
            if device_status['max_add_friend_per_day'][id][num_phone_zalo] <= 0:
                return jsonify({"status": "Đã đạt giới hạn kết bạn một ngày"})
    if num_add_friend >= max_add_friend_per_day:
        return jsonify({"status": "Đã đạt giới hạn kết bạn một ngày"})
#    ava = data['ava']
    dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
        print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    # d = u2.connect(id_device)
    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1
        dict_status_zalo[num_phone_zalo] = "add_friend_chat_pvp"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            current_phone = ""
            for it in docs:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    break
            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                    eventlet.sleep(0.2)
                d = u2.connect(id_device)
                d = switch_account(d, user_name)
                if current_phone != "":
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                        "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})
            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0] 
                return jsonify({"status": "Chuyển tài khoản thất bại"})


        try:
            d = u2.connect(id_device)
        except Exception as e:
            print("Thiết bị đã ngắt kết nối")
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return jsonify({"status": "Thiết bị đã ngắt kết nối"})

        if not device_status['active']:
            device_status['active'] = True
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                json.dump(device_status, f, indent=4)
            eventlet.sleep(0.1)
            try:
                d.app_start("com.zing.zalo", stop=True)
                # eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    eventlet.sleep(0.05)
            except Exception as e:
                print("Thiết bị đã ngắt kết nối")
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return jsonify({"status": "Thiết bị đã ngắt kết nối"})
                # if d is None:

        try:
            if d(text="Kết bạn").exists:
                d(resourceId="com.zing.zalo:id/tv_function_privacy").click()
                eventlet.sleep(1.0)
                d(resourceId="com.zing.zalo:id/btnSendInvitation").click()
                eventlet.sleep(1.0)
            else:
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return jsonify({"status": "Đã gửi kết bạn trước đó hoặc đã là bạn bè"})

        except Exception as e:
            print("Lỗi gặp phải là: ", e)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return jsonify({"status": "Gửi kết bạn thất bại"})

        for id in range(len(list_prior_chat_boxes)):
            if list_prior_chat_boxes[id]['name'] == name:
                list_prior_chat_boxes[id]['friend_or_not'] = "added"
                break
        data_update = {"num_phone_zalo": num_phone_zalo,
                       "list_prior_chat_boxes": list_prior_chat_boxes}
        update_base_document_json(
            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)
        dict_status_zalo[num_phone_zalo] = ""
        del dict_queue_device[id_device][0]
        num_add_friend += 1
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)

        for id in range(len(device_status['max_add_friend_per_day'])):
            if num_phone_zalo in device_status['max_add_friend_per_day'][id].keys():
                device_status['max_add_friend_per_day'][id][num_phone_zalo] -= 1
                # handle_chat_view(d, num_phone_zalo)

        if device_status['active'] and len(dict_queue_device[id_device]) == 0:
            device_status['active'] = False

        with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
            json.dump(device_status, f, indent=4)

        return jsonify({"status": "Gửi kết bạn thành công"})


@app.route('/api_create_group_chat_pvp', methods=['POST', 'GET'])
def api_add_create_group_chat_pvp():
    data = request.form
    list_socket_call.append("create_group_chat_pvp")
    num_phone_zalo = data.get('num_phone_zalo')
    name_group = data.get('name_group')
    mem_list_str = data.get('mem_list')
    mem_list = json.loads(mem_list_str)
    #print("Danh sách thành viên nhóm là: ", mem_list)
    ava = data.get('group_avatar')
    # global now_phone_zalo
    # now_phone_zalo = num_phone_zalo
    global num_add_friend
    global max_add_friend_per_day

    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
        device_status = json.load(f)

    # ava = data.get('ava')
    dict_status_update_pvp[num_phone_zalo] = 1
    docs = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                                 "num_phone_zalo": num_phone_zalo})
    if len(docs) > 0:
        document = docs[0]
        id_device = document['id_device']
        now_phone_zalo[id_device] = num_phone_zalo
    else:
        print(num_phone_zalo)
        #print("không có đâu")

# docs giờ là một list chứa mọi document tìm được
    id_device = document['id_device']
    dict_process_id[id_device] += 1
    id_process = dict_process_id[id_device]
    dict_queue_device[id_device].append(id_process)
    user_name = document['name']
    list_prior_chat_boxes = document['list_prior_chat_boxes']
    list_group = document['list_group']
    try:
        d = u2.connect(id_device)
        device_connect[id_device] = True
    except Exception as e:
        print("Thiết bị đã ngắt kết nối")
        device_connect[id_device] = False
        return jsonify({"status": "Thiết bị đã ngắt kết nối"})

    if (id_device in dict_devices and num_phone_zalo in dict_status_zalo.keys()):
        docs = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
        check_busy = False
        doc_phone_zalo = []
        for doc in docs:
            if doc['num_phone_zalo'] != "":
                doc_phone_zalo.append(doc['num_phone_zalo'])
                if dict_status_zalo[doc['num_phone_zalo']] != "":
                    check_busy = True
                    break
        current_id_process = dict_queue_device[id_device][0]
        while check_busy or current_id_process != id_process:
            check_busy = False
            for phone in doc_phone_zalo:
                if dict_status_zalo[phone] != "":
                    check_busy = True
            current_id_process = dict_queue_device[id_device][0]
            eventlet.sleep(0.1)

        dict_status_update_pvp[num_phone_zalo] = 1
        dict_status_zalo[num_phone_zalo] = "create_group_chat_pvp"
        doc = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
            "num_phone_zalo": num_phone_zalo})[0]
        if not doc['status']:
            docs = get_base_id_zalo_json(
                "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {"id_device": id_device})
            current_phone = ""
            for it in docs:
                if it['status']:
                    current_phone = it['num_phone_zalo']
                    break
            try:
                with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                    device_status = json.load(f)
                if not device_status['active']:
                    device_status['active'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                        json.dump(device_status, f, indent=4)
                    eventlet.sleep(0.2)
                # d = u2.connect(id_device)
                d = switch_account(d, user_name)
                if current_phone != "":
                    status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                        "num_phone_zalo": current_phone, "status": False})
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", {
                    "num_phone_zalo": num_phone_zalo, "status": True})
            except Exception as e:
                print("Chuyển tài khoản thất bại", id_device)
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return jsonify({"status": "Chuyển tài khoản thất bại"})

        try:
            d = u2.connect(id_device)
            # global device_connect
            device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối")
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            return jsonify({"status": "Thiết bị đã ngắt kết nối"})

        if not device_status['active']:
            device_status['active'] = True
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                json.dump(device_status, f, indent=4)
            eventlet.sleep(0.2)
            try:
                d.app_start("com.zing.zalo", stop=True)
                # eventlet.sleep(1.0)
                while not d(resourceId="com.zing.zalo:id/maintab_message").exists:
                    eventlet.sleep(0.05)
            except Exception as e:
                print("Thiết bị đã ngắt kết nối")
                dict_status_zalo[num_phone_zalo] = ""
                del dict_queue_device[id_device][0]
                return jsonify({"status": "Thiết bị đã ngắt kết nối"})
                # if d is None:

        try:
            d.app_start("com.zing.zalo", stop=True)
            eventlet.sleep(1.0)
            d(resourceId="com.zing.zalo:id/action_bar_plus_btn").click()
            eventlet.sleep(0.1)
            d(text="Tạo nhóm").click()
            eventlet.sleep(0.1)
            if name_group != "":
                gr_names = [group['name'] for group in list_group]
                if name_group in gr_names:
                    dict_status_zalo[num_phone_zalo] = ""
                    return jsonify({"status": "Tên nhóm này tồn tại, yêu cầu đặt tên khác"})

                d.xpath(
                    '//*[@resource-id="com.zing.zalo:id/header_section"]/android.widget.LinearLayout[1]').click()
                eventlet.sleep(0.1)
                d.send_keys(name_group, clear=True)
                eventlet.sleep(0.1)
                d(resourceId="com.zing.zalo:id/btn_done_input_group_name").click()
                eventlet.sleep(0.1)
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
                eventlet.sleep(0.1)
                d.send_keys(mem, clear=True)
                eventlet.sleep(0.1)
                # if d(textContains=mem).exists:
                #    d(textContains=mem).click()
                el = d.xpath(
                    '//android.widget.FrameLayout[@index="0" and normalize-space(@text) != ""]')
                if el.exists:
                    el.click()
                    eventlet.sleep(0.1)

            d(resourceId="com.zing.zalo:id/btn_done_create_group").click()
            eventlet.sleep(1.0)

            if d(resourceId="com.zing.zalo:id/btn_done_create_group").exists:
                dict_status_zalo[num_phone_zalo] = ""
                try:
                    d.press('back')
                    eventlet.sleep(0.1)
                    d.xpath(
                        '//*[@resource-id="com.zing.zalo:id/modal_cta_custom_layout"]/android.widget.RelativeLayout[2]').click()
                    eventlet.sleep(0.1)
                except Exception as e:
                    print("Lỗi gặp phải là: ", e)
                return jsonify({"status": "Cần tối thiểu 1 người là bạn bè"})

            list_mems = {user_name: "Trưởng nhóm"}
            for mem in mem_list:
                list_mems[mem] = ""
            check_mems = True

            list_prior_chat_boxes.append({"name": name_group, "phone": "", "ava": avatar, "time": "", "message": "",
                                         "status": "seen", "data_chat_box": [], "list_mems": list_mems, "check_mems": check_mems})
            list_prior_chat_boxes.insert(
                0, list_prior_chat_boxes.pop(-1))
            list_group.append(
                {"name": name_group, "ava": avatar, "list_mems": list_mems, "check_mems": check_mems})
        except Exception as e:
            print("Lỗi gặp phải là: ", e)
            dict_status_zalo[num_phone_zalo] = ""
            del dict_queue_device[id_device][0]
            try:
                d.press('back')
                eventlet.sleep(0.1)
                d.xpath(
                    '//*[@resource-id="com.zing.zalo:id/modal_cta_custom_layout"]/android.widget.RelativeLayout[2]').click()
                eventlet.sleep(0.1)
            except Exception as e:
                print("Lỗi gặp phải là: ", e)
            return jsonify({"status": "Tạo nhóm thất bại"})

        data_update = {"num_phone_zalo": num_phone_zalo,
                       "list_prior_chat_boxes": list_prior_chat_boxes, "list_group": list_group}
        update_base_document_json(
            "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[num_phone_zalo]}", data_update)

        dict_status_zalo[num_phone_zalo] = ""
        del dict_queue_device[id_device][0]
        dict_status_update_pvp[num_phone_zalo] = 0
        with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json', 'r') as f:
            device_status = json.load(f)
        if device_status['active'] and len(dict_queue_device[id_device]) == 0:
            device_status['active'] = False
            #print("Có set về false không")
            with open(f"C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                json.dump(device_status, f, indent=4)
        return jsonify({"status": "Tạo nhóm thành công"})


def api_log_in_status(id_device):
    print("Bắt đầu cào dữ liệu và lấy dữ liệu người dùng")

    file_path = f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json"
    # global device_connect
    global dict_devices
    # print("Id của máy là ", id_device)
    try:
        d = u2.connect(id_device)
        # d.app_start('com.zing.zalo', stop=True)
        print("Id của máy là ", id_device)
        device_connect[id_device] = True
        dict_devices.append(id_device)
    except Exception as e:
        print(e)
        print("Thiết bị đã ngắt kết nối", id_device)
        eventlet.sleep(5)
        device_connect[id_device] = False
        api_log_in_status(id_device)
        return True
    if os.path.exists(file_path):
        os.remove(file_path)  # Xóa file nếu có
    device_status = {
        "active": True,
        "max_message_per_day": [],
        "max_add_friend_per_day": [],
        "update": False

    }

    #print("Đến đây chưa nhỉ", id_device)

    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json", 'w') as f:
        json.dump(device_status, f, indent=4)

    file_path_new = f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json"
    if os.path.exists(file_path_new):
        with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json', 'r', encoding='utf-8') as f:
            zalo_data = json.load(f)
        for i in range(len(zalo_data)):
            zalo_data[i]['status'] = False
    else:
        zalo_data = []

    name_zalos = []
    try:
        # if True:
        # Lấy danh sách tên các tài khoản zalo hiện có
        d.app_start("com.zing.zalo", stop=True)
        eventlet.sleep(1.0)
        d(resourceId="com.zing.zalo:id/maintab_metab").click()
        eventlet.sleep(1.0)
        d.xpath(
            '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[2]').click()

        eventlet.sleep(1.5)
        d.swipe_ext(Direction.FORWARD)
        eventlet.sleep(1.0)
        try:
            d(resourceId="com.zing.zalo:id/itemSwitchAccount").click()
        except Exception as e:
            api_log_in_status(id_device)
            return True
        eventlet.sleep(1.0)

        # items = d.xpath("//android.widget.TextView[@text!='']").all()
        nope = ['Đã đăng nhập',
                "Chuyển tài khoản", "Thêm tài khoản để đăng nhập nhanh.", "Thêm tài khoản"]
        elements = d(resourceId="com.zing.zalo:id/name")
        zalo_name = [zalo['name']
                     for zalo in zalo_data if "name" in zalo.keys()]
        for elem in elements:
            name_zalo_1 = elem.info.get('text', '').strip()
            if name_zalo_1 not in nope:
                name_zalos.append(name_zalo_1)
                if name_zalo_1 not in zalo_name:
                    zalo_data.append({"id_device": id_device, "num_phone_zalo": "", "name": name_zalo_1, "ava": "", "list_friend": [
                    ], "list_group": [], "list_invite_friend": [], "list_prior_chat_boxes": [], "list_unseen_chat_boxes": [], "status": False})
        print(name_zalos)
        '''
        for item in items:
            name_zalo_1 = item.text
            if name_zalo_1 not in nope:
                name_zalos.append(name_zalo_1)
                zalo_data.append({"id_device": id_device, "num_phone_zalo": "", "name": name_zalo_1, "ava": "", "list_friend": [
            ], "list_group": [], "list_invite_friend": [], "list_prior_chat_boxes": [], "list_unseen_chat_boxes": [], "status": False})
        '''

        # phone_zalos = []

        # dict_device_and_phone[id_device] = phone_zalos

        # print("Các tên tài khoản zalo hiện tại là", zalo_name)

        for id in range(len(name_zalos)):
            # zalo_data[id]['status'] = True
            d.app_start("com.zing.zalo", stop=True)
            eventlet.sleep(1)
            d(resourceId="com.zing.zalo:id/maintab_metab").click()
            eventlet.sleep(1.5)
            if d(resourceId="com.zing.zalo:id/subtitle_list_me_tab").exists:
                d(resourceId="com.zing.zalo:id/subtitle_list_me_tab").click()
            else:
                d(resourceId="com.zing.zalo:id/heading_list_setting_container").click()
            eventlet.sleep(1.5)
            avatar_b64 = ""
            try:
                iv = d(resourceId="com.zing.zalo:id/rounded_avatar_frame")
                img = iv.screenshot()

                # 2. Giảm độ phân giải ảnh nhỏ hơn, vẫn giữ aspect ratio
                max_w, max_h = 200, 200
                # nhanh, giữ tỉ lệ gốc :contentReference[oaicite:1]{index=1}
                img.thumbnail((max_w, max_h), resample=Image.BILINEAR)

                # 3. Nén ảnh với JPEG (chất lượng vừa phải kèm optimize) để có kích thước tối ưu
                buf = io.BytesIO()
                # giảm kích thước, chất lượng vẫn tốt :contentReference[oaicite:2]{index=2}
                img.save(buf, format="JPEG", optimize=True, quality=75)

                # 4. Encode sang Base64 (chuỗi ASCII ngắn và nhẹ hơn)
                # Base64 chỉ chứa ký tự ASCII :contentReference[oaicite:3]{index=3}
                avatar_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            except Exception as e:
                pass
            # zalo_data[id]['ava'] = avatar_b64
            eventlet.sleep(1.0)
            d.xpath(
                '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[2]').click()
            eventlet.sleep(1.0)
            d(resourceId="com.zing.zalo:id/setting_text_primary",
              text="Thông tin").click()
            #print("Có click được không")
            eventlet.sleep(1.5)
            num_phone_zalo = d(
                resourceId="com.zing.zalo:id/tv_phone_number").get_text()
            print("Số điện thoại là: ", num_phone_zalo)
            num_phone_zalo = num_phone_zalo.replace(" ", "")
            num_phone_zalo = num_phone_zalo.replace("+84", "0")
            ck_zalo = False
            for it in range(len(zalo_data)):
                if zalo_data[it]['num_phone_zalo'] == num_phone_zalo:
                    zalo_data[it]['name'] = name_zalos[id]
                    zalo_data[it]['ava'] = avatar_b64
                    zalo_data[it]['status'] = True
                    list_prior_chat_boxes = zalo_data[it]['list_prior_chat_boxes']
                    if "check_get_lf" not in list(zalo_data[it].keys()):
                        zalo_data[it]['check_get_lf'] = False
                    ck_zalo = True
                    break
            if not ck_zalo:
                for it in range(len(zalo_data)):
                    if zalo_data[it]['name'] == name_zalos[id] and zalo_data[it]['num_phone_zalo'] != "":
                        zalo_data[it]['num_phone_zalo'] = num_phone_zalo
                        zalo_data[it]['ava'] = avatar_b64
                        zalo_data[it]['status'] = True
                        list_prior_chat_boxes = zalo_data[it]['list_prior_chat_boxes']
                        if "check_get_lf" not in list(zalo_data[it].keys()):
                            zalo_data[it]['check_get_lf'] = False
                        ck_zalo = True
                        break
            if not ck_zalo:
                # for it in range(len(zalo_data)):
                #    if zalo_data[it]['name'] == name_zalos[id] and zalo_data[it]['num_phone_zalo'] != "":
                zalo_data.append({"id_device": id_device, "num_phone_zalo": num_phone_zalo, "name": name_zalo_1, "ava": avatar_b64, "list_friend": [
                ], "list_group": [], "list_invite_friend": [], "list_prior_chat_boxes": [], "list_unseen_chat_boxes": [], "status": True, "check_get_lf": False})
                list_prior_chat_boxes = []
            # zalo_data[id]['num_phone_zalo'] = num_phone_zalo
            dict_device_and_phone[id_device].append(num_phone_zalo)
            dict_status_zalo[num_phone_zalo] = ""
            dict_status_update_pvp[num_phone_zalo] = 0
            dict_phone_device[num_phone_zalo] = id_device
            dict_process_id[num_phone_zalo] = 0
            dict_queue_device[num_phone_zalo] = []
            with open(f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json", 'w', encoding="utf-8") as f:
                json.dump(zalo_data, f, ensure_ascii=False, indent=4)
            eventlet.sleep(5.0)

            tag_name = {}
            data_chat_boxes = {}

            for chat in list_prior_chat_boxes:
                if 'tag' in list(chat.keys()):
                    if chat['tag'] != "":
                        tag_name[chat['name']] = chat['tag']
                if "data_chat_box" in list(chat.keys()):
                    if chat["data_chat_box"] != []:
                        data_chat_boxes[chat['name']] = chat["data_chat_box"]

        # phone = [zalo['num_phone_zalo'] for zalo in zalo_data if zalo['num_phone_zalo'] != ""]
        # for num_phone_zalo in phone:

            print("Bắt đầu lấy danh sách bạn bè")
            for it in range(len(zalo_data)):
                if zalo_data[it]['num_phone_zalo'] == num_phone_zalo:
                    list_friend = zalo_data[it]['list_friend']
                    check_get_lf = zalo_data[it]['check_get_lf']
                    zalo_data[it]['ava'] = avatar_b64
                    zalo_data[it]['status'] = True
                    ck_zalo = True
                    break
            result1 = api_get_list_friend(
                {"num_phone_zalo": num_phone_zalo}, check_get_lf)
            if result1:
                if not check_get_lf:
                    zalo_data[it]['check_get_lf'] = True
                    with open(f"C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json", 'w', encoding="utf-8") as f:
                        json.dump(zalo_data, f, ensure_ascii=False, indent=4)

            if not device_connect[id_device]:
                dict_devices = [dv for dv in dict_devices if dv != id_device]
                api_log_in_status(id_device)
                # dict_devices = [dv for dv in dict_devices if dv != id_device]
                return True

            print("Bắt đầu lấy danh sách nhóm")
            result2 = api_get_list_group({"num_phone_zalo": num_phone_zalo})
            if not device_connect[id_device]:
                dict_devices = [dv for dv in dict_devices if dv != id_device]
                api_log_in_status(id_device)
                # dict_devices = [dv for dv in dict_devices if dv != id_device]
                return True
            '''
            print("Bắt đầu lấy danh sách gửi kết bạn")
            result3 = api_get_list_invite_friend(
                {"num_phone_zalo": num_phone_zalo})
            if not device_connect:
                api_log_in_status(id_device)
                return True
            '''
            print("Bắt đầu lấy danh sách chat ưu tiến")
            result4 = api_update_list_prior_chat_boxes(
                {"num_phone_zalo": num_phone_zalo}, tag_name=tag_name, data_chat_boxes=data_chat_boxes)
            if not device_connect[id_device]:
                dict_devices = [dv for dv in dict_devices if dv != id_device]
                api_log_in_status(id_device)
                return True
            print("Bắt đầu lấy danh sách chat chưa đọc")
            # result5 = api_update_list_unseen_chat_boxes({"num_phone_zalo":  num_phone_zalo})

            print("Bắt đầu lấy lịch sử chat")
            try:
                for name_ntd in result4:
                    if name_ntd not in result2:
                        try:
                            result6 = api_update_data_one_chat_box(
                                {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, update=True)
                            if not device_connect[id_device]:
                                dict_devices = [
                                    dv for dv in dict_devices if dv != id_device]
                                api_log_in_status(id_device)
                                # dict_devices = [dv for dv in dict_devices if dv != id_device]
                                return True
                        except Exception as e:
                            pass
            except Exception as e:
                print(e)

            for name_ntd in result2:
                if name_ntd in result2:
                    try:
                        result6 = api_update_list_mems_one_group(
                            {"num_phone_zalo": num_phone_zalo, "name_ntd": name_ntd}, update=True)
                        if not device_connect[id_device]:
                            dict_devices = [
                                dv for dv in dict_devices if dv != id_device]
                            api_log_in_status(id_device)
                            # dict_devices = [dv for dv in dict_devices if dv != id_device]
                            return True
                    except Exception as e:
                        pass

            if id < len(zalo_data)-1:
                d = switch_account(d, name_zalos[id+1])
                status = update_base_document_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{id_device}", {
                    "num_phone_zalo": num_phone_zalo, "status": False})
                with open(f'C:/Zalo_CRM/Zalo_base/Zalo_data_login_path_{id_device}.json', 'r', encoding='utf-8') as f:
                    zalo_data = json.load(f)

    except Exception as e:
        print(e)
        print("Đã gặp lỗi trong quá trình lấy thông tin zalo")
        # eventlet.sleep(5)
        # api_log_in_status(id_device)
        # return True

    print("Cào dữ liệu thành công")
    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json', 'r') as f:
        device_status = json.load(f)
    d.app_start("com.zing.zalo", stop=True)
    eventlet.sleep(2.0)
    device_status['active'] = False
    device_status['update'] = True

    for phone in dict_device_and_phone[id_device]:
        device_status['max_message_per_day'].append({phone: 100})
        device_status['max_add_friend_per_day'].append({phone: 5})

    with open(f"C:/Zalo_CRM/Zalo_base/device_status_{id_device}.json", 'w') as f:
        json.dump(device_status, f, indent=4)
    dict_devices.append(id_device)
    print("Tiến trình bắt đầu")
    # dict_devices.append(id_device)
    # return [result1, result2, result3, result4, result5, result6]
    return True


def background_update_1vs1_loop(id_device):
    # Test thôi, nhớ bỏ dòng này đi
    # global now_phone_zalo
    global id_chat
    # global device_connect
    # device_connect = True
    # now_phone_zalo = "0867956826"

    # check_get_info_zalo = False
    while True:
        # one = time.time()
        # print("Đang không có số điện thoại nào gọi đến")

        if id_device not in list(device_connect.keys()):
            print("Thiết bị chưa được kết nối", id_device)
            eventlet.sleep(2)
            continue

        if not device_connect[id_device]:
            print("Thiết bị chưa được kết nối", id_device)
            eventlet.sleep(2)
            continue

        if now_phone_zalo[id_device] == "":
            print("Đang không có số điện thoại nào gọi đến, id là ", id_device)
            eventlet.sleep(2)
            continue

        print(
            f"Số điện thoại hiện tại của {id_device} là: ", now_phone_zalo[id_device])
        document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[now_phone_zalo[id_device]]}", {
            "num_phone_zalo": now_phone_zalo[id_device]})[0]
        id_device = document['id_device']

        if id_device not in dict_devices:
            print("Dữ liệu chưa update xong")
            eventlet.sleep(2)
            continue

        documents = get_base_id_zalo_json(
            "C:/Zalo_CRM/Zalo_base", "id_device", f"Zalo_data_login_path_{dict_phone_device[now_phone_zalo[id_device]]}", {"id_device": id_device})
        current_phone = ""
        for it in documents:
            if it['status']:
                current_phone = it['num_phone_zalo']
                if current_phone != "" and current_phone != now_phone_zalo[id_device]:
                    now_phone_zalo[id_device] = current_phone
                    document = it
                break

        #print("Chạy liên tục")
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
        curr_phone_zalo = now_phone_zalo[id_device]
        if dict_status_zalo[curr_phone_zalo] != "":
            print(dict_status_zalo[curr_phone_zalo])
            eventlet.sleep(1)
            continue
        try:
            update_d = u2.connect(id_device)
            # global device_connect
            device_connect[id_device] = True
        except Exception as e:
            print("Thiết bị đã ngắt kết nối")
            device_connect[id_device] = False
            continue

        while True:
            if dict_status_zalo[curr_phone_zalo] != "":
                print(dict_status_zalo[curr_phone_zalo])
                break
            if curr_phone_zalo != now_phone_zalo[id_device]:
                print("Số điện thoại đã bị thay đổi: ",
                      now_phone_zalo[id_device])
                break
            print("Trạng thái hiện tại là: ",
                  dict_status_zalo[curr_phone_zalo])
            btn = update_d(resourceId="com.zing.zalo:id/action_bar_title")
            #print("Có bị xung đột không")
            if btn.exists:
                # print("Không vào đây à")
                # if True:

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
                        print(el.info.get("contentDescription"))
                        print("Có tồn tại phần tử thông báo test 2")

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
                            #print(data_ntd)
                            print("Tên cuộc thông báo mới là: ", new_name_ntd)
                            check = False
                            pick = -1
                            for id in range(len(list_prior_chat_boxes)):
                                if list_prior_chat_boxes[id]['name'] == data_ntd:
                                    print("Có tồn tại nhà tuyển dụng này nhé")
                                    pick = id
                                    check = True
                                    break
                            if not check:
                                list_prior_chat_boxes.append(
                                    {"name": data_ntd, "time": "", "message": "", "status": "unseen", "data_chat_box": []})
                            #print("Đã đọc chưa nhỉ:",
                            #      list_prior_chat_boxes[pick]['status'])
                            if list_prior_chat_boxes[pick]['status'] == "seen":
                                print("Có seen đó nhé")
                                list_prior_chat_boxes[pick]['status'] = "unseen"
                                list_prior_chat_boxes.insert(
                                    0, list_prior_chat_boxes.pop(pick))
                                data_update = {"num_phone_zalo": curr_phone_zalo,
                                               "list_prior_chat_boxes": list_prior_chat_boxes}
                                ck_noti = True
                        if ck_noti:
                            #print("Đã gửi socket chưa")
                            update_base_document_json(
                                "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[curr_phone_zalo]}", data_update)
                            socketio.emit('receive_list_prior_chat_box', {
                                'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})

                    # Dừng ở đây thôi
                    # last_name_ntd = name_ntd
                    #print(name_ntd)
                    with open(f'C:/Zalo_CRM/Zalo_base/device_status_{dict_phone_device[curr_phone_zalo]}.json', 'r') as f:
                        device_status = json.load(f)
                    if device_status['active']:
                        #print("Có active không")
                        if name_ntd in name_group:
                            # if True:
                            try:
                                print("Tên nhóm là: ", name_ntd)
                                if curr_phone_zalo != now_phone_zalo[id_device]:
                                    print(
                                        "Số điện thoại hiện tại đã bị thay đổi: ", now_phone_zalo[id_device])
                                    break
                                chat_box_on_chat = api_update_data_gr_chat_box(
                                    update_d, {"num_phone_zalo": curr_phone_zalo, "name_ntd": name_ntd}, document)
                                print("Dữ liễu đoạn chat là:",
                                      chat_box_on_chat)
                            except Exception as e:
                                print("Có lỗi khi cào tin nhắn nhóm: ", e)
                                dict_status_zalo[curr_phone_zalo] = ""
                            if not chat_box_on_chat:
                                break
                            if chat_box_on_chat and len(chat_box_on_chat) > 0:
                                document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[curr_phone_zalo]}", {
                                    "num_phone_zalo": curr_phone_zalo})[0]
                                list_prior_chat_boxes = document['list_prior_chat_boxes']
                                # print("Lịch sử box chat được thêm vào là:",
                                #    chat_box_on_chat)
                                socketio.emit('receive_new_message_from_ntd', {
                                    'name_ntd': name_ntd, 'friend_or_not': friend_or_not, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, to=id_chat)
                                socketio.emit('receive_list_prior_chat_box', {
                                    'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                        else:
                            document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[curr_phone_zalo]}", {
                                "num_phone_zalo": curr_phone_zalo})[0]
                            if curr_phone_zalo != now_phone_zalo[id_device]:
                                print(
                                    "Số điện thoại hiện tại đã bị thay đổi: ", now_phone_zalo[id_device])
                                break
                            try:
                                chat_box_on_chat = api_update_data_1vs1_chat_box(
                                    update_d, {"num_phone_zalo": curr_phone_zalo, "name_ntd": name_ntd}, document)
                            except Exception as e:
                                dict_status_zalo[curr_phone_zalo] = ""
                                chat_box_on_chat = False
                            if not chat_box_on_chat:
                                break
                            if chat_box_on_chat and len(chat_box_on_chat) > 0:
                                document = get_base_id_zalo_json("C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[curr_phone_zalo]}", {
                                    "num_phone_zalo": curr_phone_zalo})[0]
                                list_prior_chat_boxes = document['list_prior_chat_boxes']
                                # print("Lịch sử box chat được thêm vào là:",
                                #    chat_box_on_chat)
                                socketio.emit('receive_new_message_from_ntd', {
                                    'name_ntd': name_ntd, 'friend_or_not': friend_or_not, 'status': "Có dữ liệu mới từ khách hàng gửi đến"}, to=id_chat)
                                socketio.emit('receive_list_prior_chat_box', {
                                    'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})
                except Exception as e:
                    dict_status_zalo[curr_phone_zalo] = ""
                    print("Lỗi gặp phải là ", e)
                    break

            else:
                break
            eventlet.sleep(3)
        ut = update_d.xpath('//*[@text="Ưu tiên"]')
        if ut.exists:
            if curr_phone_zalo != now_phone_zalo[id_device]:
                print("Số điện thoại đã bị thay đổi: ",
                      now_phone_zalo[id_device])
                continue
            print("Có tồn tại ưu tiên")
            ck_noti = False
            boxes = api_update_list_prior_chat_boxes(
                {"num_phone_zalo": curr_phone_zalo}, max_chat_boxes=8, scroll_or_not=False)

            if not boxes or len(boxes) == 0:
                eventlet.sleep(3)
                continue
            num = len(boxes)-1
            if num == -1:
                continue
            #print(boxes)
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
                    "C:/Zalo_CRM/Zalo_base", "num_phone_zalo", f"Zalo_data_login_path_{dict_phone_device[curr_phone_zalo]}", data_update)
                socketio.emit('receive_list_prior_chat_box', {
                    'user_name': user_name, 'list_prior_chat_boxes': list_prior_chat_boxes, 'status': "Có dữ liệu mới từ khách hàng gửi đến"})

        eventlet.sleep(3)


if __name__ == "__main__":

    for device_id in list(dict_device_and_phone.keys()):
        now_phone_zalo[device_id] = ""
        socketio.start_background_task(
            target=api_log_in_status, id_device=device_id)
        socketio.start_background_task(
            target=background_update_1vs1_loop, id_device=device_id)
    #socketio.run(app, host="0.0.0.0", port=8001,
    #             debug=True, use_reloader=False)
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=8001,
        debug=True,
        use_reloader=False,
        certfile="ssl/fullchain.pem",
        keyfile="ssl/privkey.pem",
        server_side=True
    )
    
