import urllib3
import json
import networkx as nx
import matplotlib.pyplot as plt
import os
import threading


CONTROLLER_IP = 'http://10.128.237.106:8080'

def get_all_switches():

    url = CONTROLLER_IP + '/stats/switches'
    http = urllib3.PoolManager()
    res = http.request('GET', url)
    res = res.data.decode('unicode_escape')
    res = json.loads(res)

    return res

def get_flow_switche_dpid():
# get flows stats of the switch filtered by the fields
    url = CONTROLLER_IP + '/stats/switches'
    http = urllib3.PoolManager()
    res = http.request('GET', url)
    res = res.data.decode('unicode_escape')
    res = json.loads(res)

    return res


#  80,100,81,1,1
post_data_ip = {
    "dpid": 3,
    "table_id": 0,
    "idle_timeout": 30,
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


add_flowentry_url = CONTROLLER_IP + "/stats/flowentry/add"

fstates_dir = 'gen_data/Lion_isls_plus_grid_twostation_algorithm_free_one_only_over_isls/dynamic_state_100000ms_for_600s'
fstates_list = sorted(os.listdir(fstates_dir))

# 60,101,61,1,1
# 61,100,51,0,3
# 2,100,92,3,3
# 2,101,92,3,3
priority_add_flow_update_router = 1

http = urllib3.PoolManager()


for fstate in fstates_list[:len(fstates_list)//2]:
    priority_add_flow_update_router +=  1
    with open(os.path.join(fstates_dir, fstate) , 'r') as f:
        lines = f.readlines()
        for line in lines:
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


            # post_data['dpid'] = next_hop_dpi







#
# r = http.request(
#     "POST",
#     add_flowentry_url,
#     body = encoded_data,
#     headers = {
#         'x-env-code':'mafutian',
#         'content-type':'application/json;charset=UTF-8'
#     }
# )

# if r.status == 200:
#     print('stats',200)
#     reponse     = r.data
#     if len(reponse) > 0:
#         j = json.loads(reponse)
#         print(j)
#
# print(r)







class MyThreading(threading.Thread):
    def __init__(self):
        super(MyThreading, self).__init__()




    def run(self):
        print('hello')
