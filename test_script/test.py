from multiprocessing import set_forkserver_preload
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink, Link, Intf
from mininet.topo import Topo
import threading
import time
import  sys
from mininet.util import quietRun
import re
# mn --controller=remote --topo=tree,2,2

class MyTopo(Topo):

    def __init__(self, **opts):
        super(MyTopo, self).__init__(self, **opts)

        switches = {}

        switches[0] = self.addSwitch('s1')
        switches[1] = self.addSwitch('s2')

        self.addLink(switches[0], switches[1], bw = 10, delay = str(120)+"ms")

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


class Change_delay_for_link(threading.Thread):
    def __init__(self, net, simulation_end_time_s, time_step_s):
        super(Change_delay_for_link, self).__init__()
        self.net = net
        self.simulation_end_time_s = simulation_end_time_s
        self.time_step_s = time_step_s

    def run(self):

        current_time = 0
        print(threading.currentThread().name)
        while current_time < self.simulation_end_time_s:
            current_time += self.time_step_s
            time.sleep(self.time_step_s)
            print('change delay')
            manageLinks()



def manageLinks():
    nodes = net.switches # + net.hosts
    print("nodes", nodes)
    for node in nodes:
        # print('node', node,'type', type(node))
        print('\nnode', node, 'node.dpid', int(node.dpid))
        changeBandwith(node)

def changeBandwith( node ):

    print("node.intfList--->", node.intfList())
    # print("node.intfNames--->", node.intfNames(), 'node.intfNames type ', type(node.intfNames()))

    for intf in node.intfList(): # loop on interfaces of node
        print('intf', intf)
        print("intf.link", intf.link, 'intf.link type', type(intf.link))
        if intf.link and type(intf.link.intf1.node) == type(intf.link.intf2.node): # get link that connects to interface(if any)
            newBW = 5
            intfs = [ intf.link.intf1, intf.link.intf2 ] #intfs[0] is source of link and intfs[1] is dst of link
            src_2_dst_nodes = [int(intf.link.intf1.node.dpid), int(intf.link.intf2.node.dpid)]
            # print('intf1 type', type(intf.link.intf1))
            # print(repr(intf.link.intf1))
            print('intfs-->', intfs )
            print('node1', intfs[0].node, 'node2', intfs[1].node)
            print('src id node1', src_2_dst_nodes[0], 'dst id node2', src_2_dst_nodes[1])

            # print('node1 type', type(intfs[0].node), 'node2 type', type(intfs[1].node))
            intfs[0].config(bw=newBW, delay='10ms')
            intfs[1].config(bw=newBW, delay='10ms')
        else:
            info( ' \n' )



def checkIntf( intf ):
    "Make sure intf exists and is not configured."
    config = quietRun( 'ifconfig %s 2>/dev/null' % intf, shell=True )
    if not config:
        error( 'Error:', intf, 'does not exist!\n' )
        exit( 1 )
    ips = re.findall( r'\d+\.\d+\.\d+\.\d+', config )
    if ips:
        error( 'Error:', intf, 'has an IP address,'
               'and is probably in use!\n' )

# url https://blog.csdn.net/remanented/article/details/96293604


REMOTE_CONTROLLER_IP = '127.0.0.1'

if __name__ == "__main__":

    intfName = sys.argv[1] if len(sys.argv) > 1 else 'enp9s0'
    info('*** Connecting to hw intf: %s' % intfName)

    info('*** Checking', intfName, '\n')
    # checkIntf(intfName)

    info('*** Creating network\n')

    lion_topo = MyTopo()
    net = Mininet(topo=lion_topo, controller=None, link=TCLink, switch=OVSKernelSwitch)
    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=6653)
    info('*** Add NAT\n')
    # net.addNAT().configDefault()
    net.start()
    # change = Change_delay_for_link(net, 600, 10)
    # change.start()
    manageLinks()
    # #VideoStreamingService(net)
    CLI(net)
    net.stop()

