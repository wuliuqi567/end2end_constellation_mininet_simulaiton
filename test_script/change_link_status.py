from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink, Link, Intf
from mininet.topo import Topo
from mininet.util import quietRun



def changeBandwith( node ):
  for intf in node.intfList(): # loop on interfaces of node
    #info( ' %s:'%intf )
    if intf.link: # get link that connects to interface(if any)
        newBW = 5
        intfs = [ intf.link.intf1, intf.link.intf2 ] #intfs[0] is source of link and intfs[1] is dst of link
        intfs[0].config(bw=newBW)
        intfs[1].config(bw=newBW)
    else:
        info( ' \n' )

def manageLinks():
    nodes = net.switches + net.hosts
    for node in nodes:
        changeBandwith(node)