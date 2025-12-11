import zalo_crm_global_variables as gvars


def create_base_document_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = gvars.json.load(f)
        existing_doc = [d for d in data if d.get(domain) != document[domain]]
        existing_doc.append(document)
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            gvars.json.dump(existing_doc, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Lỗi gặp phải là ", e)
        return False


def delete_base_document_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = gvars.json.load(f)
        existing_doc = [d for d in data if d.get(domain) != document[domain]]
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            gvars.json.dump(existing_doc, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Lỗi gặp phải là ", e)
        return False


def update_base_document_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = gvars.json.load(f)
        for id in range(len(data)):
            if data[id][domain] == document[domain]:
                for key in document.keys():
                    data[id][key] = document[key]
                break
        with open(f'{database_name}/{collection_name}.json', 'w', encoding='utf-8') as f:
            gvars.json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Lỗi gặp phải là ", e)
        return False


def get_base_id_zalo_json(database_name, domain, collection_name, document):
    try:
        with open(f'{database_name}/{collection_name}.json', 'r', encoding='utf-8') as f:
            data = gvars.json.load(f)
        cursor = []
        for d in data:
            check_key = True
            for key in document.keys():
                if d[key] != document[key]:
                    check_key = False
                    break
            if check_key:
                cursor.append(d)
        return cursor
    except Exception as e:
        return False


def already_sent(phone_number):
    with gvars.file_lock:
        if not gvars.os.path.exists(gvars.LOG_FILE):
            return False
        with open(gvars.LOG_FILE, "r", encoding="utf-8") as f:
            return phone_number in f.read()


def log_sent(phone_number):
    with gvars.file_lock:
        with open(gvars.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(phone_number + "\n")


def already_sent_number(file_path):
    if not gvars.os.path.exists(file_path):
        return False
    else:
        return True


def read_sent_number(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            s = f.read().strip()
    except Exception:
        return 0

    if s == "":
        with gvars.file_lock:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(0))
        return 0

    return int(s)


def log_sent_number(number, file_path):
    with gvars.file_lock:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(number))


def already_sent_phone_zalo(phone_number):
    with gvars.file_lock:
        if not gvars.os.path.exists(gvars.LOG_FILE):
            return False
        with open(gvars.NUM_PHONE_ZALO_FILE, "r", encoding="utf-8") as f:
            return phone_number in f.read()


def log_sent_phone_zalo(phone_number):
    with gvars.file_lock:
        with open(gvars.NUM_PHONE_ZALO_FILE, "a", encoding="utf-8") as f:
            f.write(phone_number + "\n")
