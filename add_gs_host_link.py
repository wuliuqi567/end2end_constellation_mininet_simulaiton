import time
import urllib3
import json
import os

CONTROLLER_IP = 'http://10.128.237.106:8080'
add_flowentry_url = CONTROLLER_IP + "/stats/flowentry/add"

priority_add_flow_update_router = 1


ground_dpid_list = [101, 102]

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

def get_ground_port(num:int):
    url = CONTROLLER_IP + '/stats/port/{}'.format(num)
    http = urllib3.PoolManager()
    try:
        res = http.request('GET', url)
        if res.status == 200:
            res = res.data.decode('unicode_escape')
            res = json.loads(res)
        else:
            res = None
    except urllib3.exceptions.ResponseError as e:
            print("get error", e)

    return res


def add_gs2host_link(ground_dpid_list:list, add_flowentry_url, post_data_ip:json, post_data_arp:json) -> None:

    http = urllib3.PoolManager()
    ####  add ground to host link
    print('add flow between host and gs --->')
    for gs_node_num in ground_dpid_list:

        res = get_ground_port(gs_node_num)  # num -> ground number
        gs_port_list = res['{}'.format(gs_node_num)]
        gs_port_list = [port_info['port_no'] for port_info in gs_port_list if type(port_info['port_no']) == int]
        # print(gs_port_list)
        gs_port_list = sorted(gs_port_list)

        # print(gs_port_list[-1])
        # print(sorted(port_list))

        host_eth_num = gs_port_list[-1]  #最大的端口号，因为host是最后建立的连接


        post_data_ip['dpid'] = gs_node_num
        post_data_ip['priority'] = 2
        post_data_ip["actions"][0]['port'] = host_eth_num
        post_data_ip['match']['ipv4_dst'] = '10.0.{}.{}'.format(gs_node_num//255, gs_node_num%255)

        encoded_data = json.dumps(post_data_ip).encode("utf-8")

    #
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
        except urllib3.exceptions as e:
            print("post error", e)

        # time.sleep(1)


        post_data_arp['dpid'] = gs_node_num
        post_data_arp['priority'] = 2
        post_data_arp["actions"][0]['port'] = host_eth_num
        post_data_arp['match']['arp_tpa'] = '10.0.{}.{}'.format(gs_node_num//255, gs_node_num%255)

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
        except urllib3.exceptions as e:
            print("post error", e)

def add_flow(satellite_network_routes_dir, fstate_file_name, time_step_ms):

    http = urllib3.PoolManager()
    global priority_add_flow_update_router
    with open(os.path.join(satellite_network_routes_dir, fstate_file_name), 'r') as f:
        print('route dir', os.path.join(satellite_network_routes_dir, fstate_file_name))
        # with open(os.path.join(fstate) , 'r') as f:
        lines = f.readlines()
        priority_add_flow_update_router += 1
        if priority_add_flow_update_router > 65535:
            priority_add_flow_update_router = 1
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
            post_data_ip['hard_timeout'] = time_step_ms//1000 + 20
            # post_data_ip['idle_timeout'] = time_step_ms//1000 + 20

            post_data_ip["actions"][0]['port'] = output_port
            post_data_ip['match']['ipv4_dst'] = '10.0.{}.{}'.format(des_dpid // 255, des_dpid % 255)

            # print(post_data_ip)
            encoded_data = json.dumps(post_data_ip).encode("utf-8")

            try:
                res = http.request(
                    "POST",
                    add_flowentry_url,
                    body=encoded_data,
                    headers={
                        'x-env-code': 'mafutian',
                        'content-type': 'application/json;charset=UTF-8'})
                if res.status == 200:
                    response = res.data
                    if len(response) > 0:
                        response = json.loads(response)
                else:
                    response = None
            except urllib3.exceptions.ResponseError as e:
                print("post error", e)

            post_data_arp['dpid'] = src_dpid
            post_data_arp['priority'] = priority_add_flow_update_router
            post_data_arp['hard_timeout'] = time_step_ms // 1000 + 20
            # post_data_arp['idle_timeout'] = time_step_ms // 1000 + 20

            post_data_arp["actions"][0]['port'] = output_port
            post_data_arp['match']['arp_tpa'] = '10.0.{}.{}'.format(des_dpid // 255, des_dpid % 255)

            # print(post_data_arp)
            encoded_data = json.dumps(post_data_arp).encode("utf-8")

            try:
                res = http.request(
                    "POST",
                    add_flowentry_url,
                    body=encoded_data,
                    headers={
                        'x-env-code': 'mafutian',
                        'content-type': 'application/json;charset=UTF-8'})
                if res.status == 200:
                    response = res.data
                    if len(response) > 0:
                        response = json.loads(response)
                else:
                    response = None
            except urllib3.exceptions.ResponseError as e:
                print("post error", e)

if __name__ == "__main__":

    add_gs2host_link(ground_dpid_list, add_flowentry_url, post_data_ip, post_data_arp)
