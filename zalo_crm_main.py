import zalo_crm_global_variables as gvars
from zalo_crm_background_functions import background_first_crawl_per_day, background_update_data_loop
import zalo_crm_api_interact_functions, zalo_crm_get_data_from_database, zalo_crm_socket_interact_functions
if __name__ == "__main__":
    for device_id in list(gvars.dict_device_and_phone.keys()):
        gvars.now_phone_zalo[device_id] = ""
        gvars.dict_process_id[device_id] = 0
        gvars.dict_queue_device[device_id] = []
        gvars.dict_id_chat[device_id] = ""
        gvars.dict_device_and_phone[device_id] = []
        gvars.socketio.start_background_task(
            target=background_first_crawl_per_day, id_device=device_id)
        gvars.socketio.start_background_task(
            target=background_update_data_loop, id_device=device_id)
    #gvars.socketio.run(gvars.app, host="0.0.0.0", port=8001,
    #                   debug=True, use_reloader=False)
    
    gvars.socketio.run(
        gvars.app,
        host="0.0.0.0",
        port=8001,
        debug=True,
        use_reloader=False,
        certfile="ssl/fullchain.pem",
        keyfile="ssl/privkey.pem",
        server_side=True
    )
    
