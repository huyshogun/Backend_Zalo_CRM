
import zalo_crm_global_variables as gvars
from zalo_crm_crud_database import already_sent_number, read_sent_number, log_sent_number
import re


def print_usage():
    cpu_percent = gvars.psutil.cpu_percent()
    ram_percent = gvars.psutil.virtual_memory().percent
    print(f"CPU Usage: {cpu_percent}%")
    print(f"RAM Usage: {ram_percent}%")


def switch_account(d: gvars.u2.Device, name, retire=3):

    d.app_start("com.zing.zalo", stop=True)
    # d = run_start(d)
    # d.implicitly_wait(3.0)
    gvars.eventlet.sleep(1.0)
    d(resourceId="com.zing.zalo:id/maintab_metab").click()
    gvars.eventlet.sleep(1.0)
    d.xpath(
        '//*[@resource-id="com.zing.zalo:id/zalo_action_bar"]/android.widget.LinearLayout[2]').click()

    gvars.eventlet.sleep(1.0)
    d.swipe_ext(gvars.u2.Direction.FORWARD)
    gvars.eventlet.sleep(1.0)

    d(resourceId="com.zing.zalo:id/itemSwitchAccount").click()

    gvars.eventlet.sleep(1.0)
    d.xpath(f"//android.widget.TextView[@text='{name}']").click()
    gvars.eventlet.sleep(5)
    d(resourceId="com.zing.zalo:id/btn_chat_gallery_done").click()
    gvars.eventlet.sleep(1.5)
    return d


def handle_chat_view(d: gvars.u2.Device,  num_phone_zalo):
    gvars.last_time[num_phone_zalo] = gvars.time.time()
    while True:
        time_period = gvars.time.time() - gvars.last_time[num_phone_zalo]
        if gvars.dict_status_update_pvp[num_phone_zalo] == 1:
            break

        if time_period >= 75.0:
            gvars.dict_status_update_pvp[num_phone_zalo] = 0
            name_ntd = d(
                resourceId="com.zing.zalo:id/action_bar_title")
            if name_ntd.exists:
                try:
                    while not d.xpath('//*[@text="Ưu tiên"]').exists:
                        d.press("back")
                        gvars.eventlet.sleep(0.1)
                except Exception as e:
                    print(e)
                    gvars.dict_status_zalo[num_phone_zalo] = ""

        if time_period >= 120.0:
            with open(f'C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json', 'r') as f:
                device_status = gvars.json.load(f)
            if device_status['active']:
                device_status['active'] = False
                print("Có set về false không")
                with open(f"C:/Zalo_CRM/Zalo_base/device_status_{gvars.dict_phone_device[num_phone_zalo]}.json", 'w') as f:
                    gvars.json.dump(device_status, f, indent=4)
            break
        gvars.eventlet.sleep(2)


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


def safe_click(d, cx, cy, unwanted_resid="com.zing.zalo:id/chat_layout_group_topic"):
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

    elm = d(resourceId="com.zing.zalo:id/tv_function_privacy")
    if elm.exists:
        try:
            print('Có phần tử Kết bạn')
            bounds = elm.info.get('bounds')
            top, bottom = bounds['top'], bounds['bottom']
            if top <= cy <= bottom:
                cy = bottom + 5
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
    print(f"Clicked at ({cx}, {cy})")
    # nếu phần tử không tồn tại hoặc không chặn: click bình thường
    d.long_click(cx, cy, duration=1.0)
    return d


def safe_normal_click(d, cx, cy, unwanted_resid="com.zing.zalo:id/chat_layout_group_topic"):
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
                cy = top - 5
        except Exception as e:
            print("Đã xảy ra Exception", e)

    elm = d(resourceId="com.zing.zalo:id/tv_function_privacy")
    if elm.exists:
        try:
            print('Có phần tử Kết bạn')
            bounds = elm.info.get('bounds')
            top, bottom = bounds['top'], bounds['bottom']
            if top <= cy <= bottom:
                cy = bottom + 5
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
            d.click(alt_x, alt_y)
            return d

        # nếu toạ độ nằm trong vùng cấm
        if top <= cy <= bottom:
            new_x = cx
            new_y = bottom + 5
            d.click(new_x, new_y)
            return d
    print(f"Clicked at ({cx}, {cy})")
    # nếu phần tử không tồn tại hoặc không chặn: click bình thường
    d.click(cx, cy)
    return d


def load_data_chat_box_json(data_chat_box_path):
    data_chat_box = []

    if isinstance(data_chat_box_path, list):
        return data_chat_box_path

    if not data_chat_box_path:
        return data_chat_box
    try:
        with open(data_chat_box_path, 'r', encoding='utf-8') as f:
            data_chat_box = gvars.json.load(f)
    except Exception as e:
        print("Có lỗi xảy ra trong quá trình lấy lịch sử chat ", e)

    return data_chat_box


def dump_data_chat_box_json(data_chat_box_path, data_chat_box):
    
    if data_chat_box_path and not isinstance(data_chat_box_path, list):
        with open(data_chat_box_path, "w", encoding="utf-8") as f:
            gvars.json.dump(data_chat_box, f, ensure_ascii=False, indent=4)

    else:
        if not already_sent_number(gvars.DATA_CHAT_BOX_NUMBER_PATH):
            data_chat_box_number = 0
        else:
            data_chat_box_number = read_sent_number(
                gvars.DATA_CHAT_BOX_NUMBER_PATH)
        data_chat_box_path = f"{gvars.IMAGE_FILE_DATA_PATH}/data_chat_box_{data_chat_box_number}.json"

        with open(data_chat_box_path, "w", encoding="utf-8") as f:
            gvars.json.dump(data_chat_box, f, ensure_ascii=False, indent=4)

        log_sent_number(data_chat_box_number+1,
                        gvars.DATA_CHAT_BOX_NUMBER_PATH)

    return data_chat_box_path
