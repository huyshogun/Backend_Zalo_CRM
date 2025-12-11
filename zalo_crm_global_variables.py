import eventlet
eventlet.monkey_patch()
import sys
from flask_cors import CORS
from flask import Flask, request, jsonify
import uiautomator2 as u2
from threading import Lock
import base64
import psutil
from datetime import datetime, date, timedelta
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import os
import re
import json
from PIL import Image, ImageFilter
import io


app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, async_mode='eventlet',
                    max_http_buffer_size=1024 * 1024 * 1024, cors_allowed_origins='*')

dict_status_zalo = {}
dict_status_update_pvp = {}
dict_phone_device = {}
dict_id_chat = {}
dict_device_and_phone = {}
dict_process_id = {}
dict_queue_device = {}
dict_new_friend = {}
last_time = {}
max_message_per_day = 300
num_message = 0
num_add_friend = 0
image_number = 300
max_add_friend_per_day = 30
device_connect = {}
now_phone_zalo = {}
driver = {}
list_socket_call = []

LOG_FILE = "sent_log.txt"
IMAGE_FILE_DATA_PATH = "C:/Zalo_CRM/Zalo_base/Zalo_image_file_data"
AVA_NUMBER_PATH = "C:/Zalo_CRM/Zalo_base/Zalo_image_file_data/ava.txt"
MES_NUMBER_PATH = "C:/Zalo_CRM/Zalo_base/Zalo_image_file_data/mes.txt"
DATA_CHAT_BOX_NUMBER_PATH = "C:/Zalo_CRM/Zalo_base/Zalo_image_file_data/data_chat_box.txt"
NUM_PHONE_ZALO_FILE = "C:/Zalo_CRM/Zalo_base/num_phone_zalo.txt"
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
    "EIFYAALRK7U4MRZ9": [],  # A20
    "R8YY70F81TV": [],  # A21
    "69QGMN8PXWDYPNIF": [],  # A22
    "IZDEGA8TFYXWRK9X": [],  # A23
    "R8YY70HCNRX": [],  # A24
    "R83Y50JZK6A": [],  # A25
    "R8YY70F5VSE": [] #A26
}

id_port = {
    "22773024": [{"A02": "7DXCUKKB6DVWDAQO"}, {"A06": "CEIN4X45I7ZHFEFU"}, {"A05": "UWJJOJLB85SO7LIZ"}, {"A03": "TSPNH6GYZLPJBY6X"}, {"A04": "7HYP4T4XTS4DXKCY"}, {"A01": "R8YY70F5MKN"}, {"A22": "69QGMN8PXWDYPNIF"}, {"A23": "IZDEGA8TFYXWRK9X"}],  # Sếp
    "22614471": [{"A02": "7DXCUKKB6DVWDAQO"}, {"A06": "CEIN4X45I7ZHFEFU"}, {"A05": "UWJJOJLB85SO7LIZ"}, {"A03": "TSPNH6GYZLPJBY6X"}, {"A04": "7HYP4T4XTS4DXKCY"}, {"A01": "R8YY70F5MKN"}],  # Lê Thị Liên
    "22616467": [{"A17": "EM4DYTEITCCYJNFU"}],  # Hoàng Thị Thùy Linh
    # Chị Ngô Dung
    "22615833": [{"A09": "9PAM7DIFW87DOBEU"}, {"A06": "CEIN4X45I7ZHFEFU"}],
    # Chị Bích Ngọc
    "22814414": [{"A19": "Z5LVOF4PRGXGTS9H"}, {"A02": "7DXCUKKB6DVWDAQO"}],
    # Chị Lại Thị Nhàn
    "22789191": [{"A14": "F6NZ5LRKWWGACYQ8"}, {"A01": "R8YY70F5MKN"}],
    # Chị Thư
    "22833463": [{"A15": "QK8TEMKZMBYHPV6P"}, {"A03": "TSPNH6GYZLPJBY6X"}],
    # Chị Thùy
    "22636101": [{"A16": "IJP78949G69DKNHM"}, {"A05": "UWJJOJLB85SO7LIZ"}],
    # Huyền Trang
    "22896992": [{"A13": "EY5H9DJNIVNFH6OR"}, {"A04": "7HYP4T4XTS4DXKCY"}],
    "22911349": [{"A24": "R8YY70HCNRX"}],  # Diễm Quỳnh
    "22889226": [{"A08": "CQIZKJ8P59AY7DHI"}],  # Chị Ngọc Hà
    "22894754": [{"A07": "8HMN4T9575HAQWLN"}],  # Chị Hải Yến
    "22889521": [{"A18": "PN59BMHYPFXCPN8T"}],  # Chị Ngọc Mai
    "22735395": [{"A10": "EQLNQ8O7EQCQPFXG"}],  # Chị Tâm
    "22897894": [{"A11": "YH9TSS7XCMPFZHNR"}],  # Ngọc Anh
    "22846624": [{"A20": "EIFYAALRK7U4MRZ9"}],  # Ngọc Ánh
    "22846622": [{"A21": "R8YY70F81TV"}],  # Thu Trà
    "22891672": [{"A12": "MJZDFY896TMJBUPN"}],  # Phạm Linh Chi
    "22907106": [{"A25": "R83Y50JZK6A"}],  # Vân Anh
    # Thằng đẻ ra ứng dụng
    "22862103": [{"A08": "CQIZKJ8P59AY7DHI"}, {"A04": "7HYP4T4XTS4DXKCY"}, {"A01": "R8YY70F5MKN"}],
    # Phạm Huy dùng để test
    "22858638": [{"A02": "7DXCUKKB6DVWDAQO"}, {"A05": "UWJJOJLB85SO7LIZ"}, {"A09": "9PAM7DIFW87DOBEU"}]

}
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

for device_id in dict_device_and_phone.keys():
    for phone_zalo in dict_device_and_phone[device_id]:
        dict_status_zalo[phone_zalo] = ""
        dict_status_update_pvp[phone_zalo] = 0
        dict_phone_device[phone_zalo] = device_id

try:
    if not os.path.exists(NUM_PHONE_ZALO_FILE):
        with open(NUM_PHONE_ZALO_FILE, "w", encoding="utf-8") as f:
            f.write(str(0))
    with open(NUM_PHONE_ZALO_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    list_phone_number_zalo = [l for l in raw.split(
        "\n") if l.strip()]
    for phone in list_phone_number_zalo:
        dict_new_friend[phone] = {}
except Exception as e:
    print("Không lấy được danh sách các số điện thoại tài khoản zalo")
    list_phone_number_zalo = []
