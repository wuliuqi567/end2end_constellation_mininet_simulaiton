import os
from add_gs_host_link import *

CONTROLLER_IP = 'http://10.128.237.106:8080'
add_flowentry_url = CONTROLLER_IP + "/stats/flowentry/add"

# ground_dpid_list = [226,227,228,229,230,231,232,233,234]


ground_dpid_list = [101, 102]

#  80,100,81,1,1
post_data_ip = {
    "dpid": 3,
    "table_id": 0,
    "idle_timeout": 0,
    "hard_timeout": 0,
    "priority": 1,
    "flags": 1,
    "match":{
        "ipv4_dst": "10.0.0.2",
        "eth_type": 2048
    },
    "actions":[
        {
            "type":"OUTPUT",
            "port": 1
        }
    ]
 }

post_data_arp = {
    "dpid": 1,
    "table_id": 0,
    "idle_timeout": 0,
    "hard_timeout": 0,
    "priority": 3,
    "flags": 1,
    "match":{
         "eth_type": 2054,
         "arp_tpa": "10.0.0.2"
    },
    "actions":[
        {
            "type":"OUTPUT",
            "port": 1
        }
    ]
 }



fstates_dir = 'gen_data/Lion_isls_plus_grid_twostation_algorithm_free_one_only_over_isls/dynamic_state_100000ms_for_600s'
# fstates_dir = 'gen_data2/Lion_isls_plus_grid_ground_stations_top_10_algorithm_free_one_only_over_isls/dynamic_state_120000ms_for_1200s'
fstates_list = sorted(os.listdir(fstates_dir))

test_file = ['gen_data1/Lion_isls_plus_grid_ground_stations_top_10_algorithm_free_one_only_over_isls/dynamic_state_120000ms_for_1200s/fstate_0.txt']

# 60,101,61,1,1
# 61,100,51,0,3
# 2,100,92,3,3
# 2,101,92,3,3
priority_add_flow_update_router = 1

http = urllib3.PoolManager()

#add gs2host link
add_gs2host_link(ground_dpid_list, add_flowentry_url, post_data_ip, post_data_arp)

#add fstate link
# for fstate in fstates_list[:len(fstates_list)//2]:
for fstate in fstates_list[0:1]:
# for fstate in test_file:
    priority_add_flow_update_router += 1
    # time.sleep(30)
    print('file= ', fstate)
    with open(os.path.join(fstates_dir, fstate) , 'r') as f:
    # with open(os.path.join(fstate) , 'r') as f:
        lines = f.readlines()

        for line in lines:
            # print('add forward tabele : {}'.format(line))
            line_list = [int(i) for i in line.split(',')]
            src_dpid = line_list[0] + 1
            des_dpid = line_list[1] + 1
            next_hop_dpid = line_list[2] + 1
            output_port = line_list[3] + 1
            next_hop_input_port = line_list[4] + 1

            post_data_ip['dpid'] = src_dpid
            post_data_ip['priority'] = priority_add_flow_update_router
            post_data_ip["actions"][0]['port'] = output_port
            post_data_ip['match']['ipv4_dst'] = '10.0.{}.{}'.format(des_dpid // 255, des_dpid % 255)

            # print(post_data_ip)
            encoded_data = json.dumps(post_data_ip).encode("utf-8")

            try :
                res = http.request(
                "POST",
                add_flowentry_url,
                body = encoded_data,
                headers = {
                    'x-env-code':'mafutian',
                    'content-type':'application/json;charset=UTF-8'})
                if res.status == 200:
                    response = res.data
                    if len(response) > 0:
                         response = json.loads(response)
                else:
                    response = None
            except urllib3.exceptions.ResponseError as e:
                print("post error", e)

            # time.sleep(1)

            post_data_arp['dpid'] = src_dpid
            post_data_arp['priority'] = priority_add_flow_update_router
            post_data_arp["actions"][0]['port'] = output_port
            post_data_arp['match']['arp_tpa'] = '10.0.{}.{}'.format(des_dpid // 255, des_dpid % 255)

            # print(post_data_arp)
            encoded_data = json.dumps(post_data_arp).encode("utf-8")

            try :
                res = http.request(
                "POST",
                add_flowentry_url,
                body = encoded_data,
                headers = {
                    'x-env-code':'mafutian',
                    'content-type':'application/json;charset=UTF-8'})
                if res.status == 200:
                    response = res.data
                    if len(response) > 0:
                         response = json.loads(response)
                else:
                    response = None
            except urllib3.exceptions.ResponseError as e:
                print("post error", e)

            # time.sleep(1)










