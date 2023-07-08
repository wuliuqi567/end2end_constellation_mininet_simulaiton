import urllib3
import json
import time
import networkx as nx
import matplotlib.pyplot as plt
import os
import threading
from operator import attrgetter

CONTROLLER_IP = 'http://127.0.0.1:8080'
baseURL = 'http://10.128.237.106:8080/stats/port/'

dpids =[1]


http = urllib3.PoolManager()
paths = {}        #store the shortest path
datapaths = {}
bw = {} #bw[dpid][port][r,t,remain->n]

"""
bw = {
    1:{1:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2},
       2:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2},
       3:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2}},
    2:{1:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2},
       2:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2},
       3:{'rx_bytes':22, 'tx_bytes':222, 'duration_sec':22, 'reamainBW':2}}
}
"""
# bw_m = {
#             1:{1: 10,2: 10,3: 5,4: 5, 5:10},
#             2:{1: 10,2: 3},
#             3:{1: 5,2: 3,3: 3},
#             4:{1: 3,2: 5},
#             5:{1: 5,2: 3,3: 3,4: 8},
#             6:{1: 3,2: 3,3: 2,4: 8},
#             7:{1: 5,2: 3,3: 5},
#             8:{1: 2,2: 8,3: 4,4: 5},
#             9:{1: 5,2: 5,3: 8,4: 10}
#                     }

bw_m = {
            1:{1: 10,2: 10},
            2:{1: 10,2: 10}
}

def gen_init_bw(dpid_nums:int):

    init_bw = {}

    for dpid in range(1, dpid_nums + 1):
        init_bw.setdefault(dpid,{})
        init_bw[dpid].setdefault()

clock = 30

while(clock):

    clock -=1
    # print('bw', bw)
    time.sleep(2)
    for dpid in dpids:
        try:
            res = http.request('GET', baseURL+'{}'.format(dpid))
            if res.status == 200:
                res = res.data.decode('unicode_escape')
                res = json.loads(res)
                # print(res)

                ports_stat = res['{}'.format(dpid)]
                ports_stat = ports_stat[1:]
                for stat in ports_stat:

                    # print(stat)
                    bw.setdefault(dpid, {})
                    bw[dpid].setdefault(stat['port_no'], {})
                    if 'reamainBW' not in bw[dpid][stat['port_no']]:
                        print('remain_bw')
                        bw[dpid][stat['port_no']]['rx_bytes']=stat['rx_bytes']
                        bw[dpid][stat['port_no']]['tx_bytes']=stat['tx_bytes']
                        bw[dpid][stat['port_no']]['duration_sec']=stat['duration_sec']
                        bw[dpid][stat['port_no']]['reamainBW']=10
                        continue

                    rx_bytes=stat['rx_bytes']-bw[dpid][stat['port_no']]['rx_bytes']
                    tx_bytes=stat['tx_bytes']-bw[dpid][stat['port_no']]['tx_bytes']
                    duration_sec = stat['duration_sec']-bw[dpid][stat['port_no']]['duration_sec']

                    # print('tx_bytes', tx_bytes)
                    # print('duration_sex', duration_sec)
                    # print('ssss',(rx_bytes+tx_bytes)/duration_sec*8)

                    tmp_bw=(rx_bytes+tx_bytes)/duration_sec*8/1048576
                    tmp_bw = round(tmp_bw,3)
                    print('have used bw',tmp_bw)

                    if dpid in bw_m and stat['port_no'] in bw_m[dpid]:
                        bw[dpid][stat['port_no']]['reamainBW']=bw_m[dpid][stat['port_no']]-tmp_bw

                    bw[dpid][stat['port_no']]['rx_bytes'] = stat['rx_bytes']
                    bw[dpid][stat['port_no']]['tx_bytes'] = stat['tx_bytes']
                    bw[dpid][stat['port_no']]['duration_sec'] = stat['duration_sec']


        except urllib3.exceptions.ResponseError as e:
            print('get error')




