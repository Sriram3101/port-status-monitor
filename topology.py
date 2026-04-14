"""
Custom Mininet topology for Port Status Monitoring project.
Creates: 1 switch, 4 hosts

       h1
       |
h2 -- s1 -- h3
       |
       h4

Run with:
    sudo python3 topology.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time


def create_topology():
    setLogLevel("info")

    # Use RemoteController so Ryu can connect
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    info("*** Creating controller\n")
    c0 = net.addController("c0", ip="127.0.0.1", port=6633)

    info("*** Creating switch\n")
    s1 = net.addSwitch("s1", protocols="OpenFlow13")

    info("*** Creating hosts\n")
    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    h3 = net.addHost("h3", ip="10.0.0.3/24")
    h4 = net.addHost("h4", ip="10.0.0.4/24")

    info("*** Creating links\n")
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    info("*** Starting network\n")
    net.build()
    c0.start()
    s1.start([c0])

    info("*** Waiting for controller to connect...\n")
    time.sleep(3)

    info("\n*** Network is ready!\n")
    info("*** Topology: h1, h2, h3, h4 all connected to s1\n")
    info("*** Ryu controller should be running on port 6633\n\n")
    info("*** TIP: To simulate port DOWN, run in another terminal:\n")
    info("***      sudo ip link set s1-eth1 down\n")
    info("***      sudo ip link set s1-eth1 up\n\n")

    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == "__main__":
    create_topology()
