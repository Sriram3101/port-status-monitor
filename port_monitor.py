"""
Port Status Monitoring Tool - SDN Mini Project
UE24CS252B - Computer Networks
Project #13

Uses Ryu Controller to:
- Monitor OpenFlow switch port status changes
- Detect port UP / DOWN events
- Log all changes to a file
- Print alerts to console
- Display current port status table
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
import datetime
import logging
import os

# ── Logging setup ──────────────────────────────────────────────────────────────
LOG_FILE = "port_events.log"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PortMonitor")

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                               datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class PortMonitor(app_manager.RyuApp):
    """Ryu application that monitors port status and logs every change."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PortMonitor, self).__init__(*args, **kwargs)
        # port_status[dpid][port_no] = "UP" | "DOWN"
        self.port_status = {}
        self.event_count = 0
        logger.info("=" * 60)
        logger.info("Port Monitor started")
        logger.info("=" * 60)
        print("\n" + "=" * 60)
        print("  PORT STATUS MONITORING TOOL - SDN Mini Project")
        print("=" * 60)
        print(f"  Log file: {os.path.abspath(LOG_FILE)}")
        print("=" * 60 + "\n")

    # ── Switch handshake ───────────────────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install a table-miss flow rule so packets reach the controller."""
        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        dpid     = datapath.id

        # Initialise port table for this switch
        self.port_status[dpid] = {}

        # Table-miss entry: send unmatched packets to controller
        match  = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod  = parser.OFPFlowMod(datapath=datapath, priority=0,
                                  match=match, instructions=inst)
        datapath.send_msg(mod)

        msg = f"Switch connected  dpid={dpid:#016x}"
        logger.info(msg)
        print(f"[SWITCH CONNECTED]  dpid={dpid:#016x}")

    # ── Port status events ─────────────────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Called whenever a port goes UP or DOWN."""
        msg      = ev.msg
        datapath = msg.datapath
        dpid     = datapath.id
        ofproto  = datapath.ofproto
        desc     = msg.desc
        port_no  = desc.port_no
        port_name = desc.name.decode("utf-8").strip("\x00")
        reason   = msg.reason
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine new state from port config / state flags
        link_down = bool(desc.state & ofproto.OFPPS_LINK_DOWN)
        new_state = "DOWN" if link_down else "UP"

        # Map reason code to human-readable string
        reason_map = {
            ofproto.OFPPR_ADD:    "PORT_ADDED",
            ofproto.OFPPR_DELETE: "PORT_DELETED",
            ofproto.OFPPR_MODIFY: "PORT_MODIFIED",
        }
        reason_str = reason_map.get(reason, f"REASON_{reason}")

        # Record previous state
        prev_state = self.port_status.get(dpid, {}).get(port_no, "UNKNOWN")

        # Update our table
        if dpid not in self.port_status:
            self.port_status[dpid] = {}
        self.port_status[dpid][port_no] = new_state
        self.event_count += 1

        # ── Log and alert ──────────────────────────────────────────────────────
        log_line = (
            f"Event #{self.event_count:04d} | "
            f"dpid={dpid:#016x} | "
            f"port={port_no} ({port_name}) | "
            f"reason={reason_str} | "
            f"state={prev_state} -> {new_state}"
        )
        logger.info(log_line)

        # Console alert with visual emphasis
        arrow = "▲" if new_state == "UP" else "▼"
        color_tag = "UP  " if new_state == "UP" else "DOWN"
        print(f"\n{'='*55}")
        print(f"  ALERT  [{timestamp}]")
        print(f"  {arrow} Port {color_tag} | Switch {dpid:#016x}")
        print(f"  Port number : {port_no}")
        print(f"  Port name   : {port_name}")
        print(f"  Reason      : {reason_str}")
        print(f"  Change      : {prev_state} -> {new_state}")
        print(f"{'='*55}\n")

        # Show updated status table after every event
        self._print_status_table()

    # ── Packet-in handler (learning switch logic) ──────────────────────────────
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Basic learning switch: installs flow rules so future traffic is
        forwarded directly between hosts without involving the controller.
        This fulfils the 'packet_in + match-action' requirement.
        """
        msg      = ev.msg
        datapath = msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        in_port  = msg.match["in_port"]

        pkt  = packet.Packet(msg.data)
        eth  = pkt.get_protocols(ethernet.ethernet)[0]
        dst  = eth.dst
        src  = eth.src
        dpid = datapath.id

        # MAC address table
        if dpid not in self.port_status:
            self.port_status[dpid] = {}

        # Use port_status dict as MAC table (reuse same dict, different key type)
        mac_table = getattr(self, "_mac_table", {})
        if not hasattr(self, "_mac_table"):
            self._mac_table = {}
        self._mac_table.setdefault(dpid, {})
        self._mac_table[dpid][src] = in_port

        out_port = self._mac_table[dpid].get(dst, ofproto.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rule if destination is known
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            inst  = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod   = parser.OFPFlowMod(
                datapath=datapath,
                priority=1,
                match=match,
                instructions=inst,
                idle_timeout=30,
                hard_timeout=120,
            )
            datapath.send_msg(mod)

        # Forward current packet
        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out  = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    # ── Helper: print status table ─────────────────────────────────────────────
    def _print_status_table(self):
        """Print a formatted table of current port states."""
        print("\n--- Current Port Status Table ---")
        print(f"  {'Switch (dpid)':<22} {'Port':<6} {'State'}")
        print(f"  {'-'*22} {'-'*6} {'-'*6}")
        for dpid, ports in self.port_status.items():
            for port_no, state in sorted(ports.items()):
                indicator = "UP  ▲" if state == "UP" else "DOWN ▼"
                print(f"  {dpid:#016x}  {port_no:<6} {indicator}")
        print(f"  Total events logged: {self.event_count}")
        print("-" * 35 + "\n")
