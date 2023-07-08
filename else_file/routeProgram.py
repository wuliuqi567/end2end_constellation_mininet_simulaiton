from multiprocessing import set_forkserver_preload
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink, Link, Intf
from mininet.topo import Topo

import os
import time
import math
import ephem
from astropy.time import Time
from astropy import units as u
import numpy as np
import networkx as nx

sat_net_graph_with_only_mesh_sat = nx.Graph()


# mn --controller=remote --topo=tree,2,2


class MyTopo(Topo):

    def __init__(self, mesh_net, **opts):
        super(MyTopo, self).__init__(self, **opts)
        self.mesh_net = mesh_net
        switches = {}


        switches[0] = self.addSwitch('s1')
        switches[1] = self.addSwitch('s2')

        self.addLink(switches[0], switches[1])

        # for i in range(4):
        #     switch_name = 's{}'.format(i)
        #     dpid_name = '000000000000000{}'.format(i)
        #     switches[i] = self.addSwitch(switch_name, dpid = dpid_name)

        # test_list = [(0,1), (0, 2), (1, 3), (2, 3)]
        # for a,b in test_list:
        #     self.addLink(switches[a], switches[b])

        h1 = self.addHost('h1')

        self.addLink(h1, switches[0])

        h2 = self.addHost('h2')
        self.addLink(h2, switches[1])


REMOTE_CONTROLLER_IP = '127.0.0.1'

if __name__ == "__main__":
    lion_topo = MyTopo()
    net = Mininet(topo=lion_topo, controller=None, link=TCLink, switch=OVSKernelSwitch)
    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=6653)
    net.start()
    # #VideoStreamingService(net)
    CLI(net)
    net.stop()