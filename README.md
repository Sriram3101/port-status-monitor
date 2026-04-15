# Port Status Monitoring Tool
**SDN Mininet Simulation Project – UE24CS252B Computer Networks**

## Problem Statement
Design and implement an SDN-based Port Status Monitoring Tool using Mininet and the Ryu OpenFlow controller. The tool must:
- Detect port UP / DOWN events on OpenFlow switches in real time
- Log every change with a timestamp to a persistent log file
- Generate console alerts on state transitions
- Display a live port status table after each event

---

## Architecture

```
[Mininet Topology] --OpenFlow--> [Ryu Controller] --> [Port Monitor App]
     4 hosts + 1 switch              port_monitor.py       |
                                                      ┌────┴─────┐
                                                  Log file   Console alerts
                                               port_events.log
```

---

## Setup & Execution Steps


### Step 1 – Start the Ryu controller (Terminal 1)
```bash
ryu-manager port_monitor.py --observe-links
```
Keep this terminal open. All alerts and the port status table appear here.

### Step 2 – Start the Mininet topology (Terminal 2)
```bash
sudo python3 topology.py
```
This creates 1 switch (s1) and 4 hosts (h1–h4) and connects to the Ryu controller.

### Step 3 – Test connectivity (inside Mininet CLI)
```
mininet> pingall
```
Expected: 0% packet loss

### Step 4 – Run test scenarios (Terminal 3)
```bash
sudo python3 test_scenarios.py
```

Or manually trigger events:
```bash
# Bring a port DOWN
sudo ip link set s1-eth1 down

# Bring the port back UP
sudo ip link set s1-eth1 up
```

### Step 5 – View flow tables
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 dump-ports s1
```

### Step 6 – View logs
```bash
cat port_events.log
```

---

## Expected Output

### Ryu terminal (port DOWN alert)
```
=======================================================
  ALERT  [2025-01-15 14:32:10]
  ▼ Port DOWN | Switch 0x0000000000000001
  Port number : 1
  Port name   : s1-eth1
  Reason      : PORT_MODIFIED
  Change      : UP -> DOWN
=======================================================
```

### Ryu terminal (port UP alert)
```
=======================================================
  ALERT  [2025-01-15 14:32:45]
  ▲ Port UP   | Switch 0x0000000000000001
  Port number : 1
  Port name   : s1-eth1
  Reason      : PORT_MODIFIED
  Change      : DOWN -> UP
=======================================================
```

### port_events.log sample
```
2025-01-15 14:30:00  INFO     Port Monitor started
2025-01-15 14:30:05  INFO     Switch connected  dpid=0x0000000000000001
2025-01-15 14:32:10  INFO     Event #0001 | dpid=0x0000000000000001 | port=1 (s1-eth1) | reason=PORT_MODIFIED | state=UP -> DOWN
2025-01-15 14:32:45  INFO     Event #0002 | dpid=0x0000000000000001 | port=1 (s1-eth1) | reason=PORT_MODIFIED | state=DOWN -> UP
```

---

## Test Scenarios

| Scenario | Action | Expected Result |
|----------|--------|-----------------|
| 1 – Port DOWN | `sudo ip link set s1-eth1 down` | Alert printed, DOWN logged |
| 2 – Port UP   | `sudo ip link set s1-eth1 up`   | Alert printed, UP logged   |

---

## Performance Observations

### Latency (ping)
```bash
# Inside Mininet CLI
mininet> h1 ping -c 10 h2
```

### Throughput (iperf)
```bash
# Inside Mininet CLI
mininet> iperf h1 h2
```

---

## SDN Concepts Explained

**What is packet_in?**
A `packet_in` event occurs when a switch receives a packet it has no matching flow rule for. The switch forwards the packet to the controller. The controller then decides what to do and installs a flow rule so future similar packets are handled locally by the switch (no controller involvement needed).

**What is a flow rule?**
A flow rule = match fields + actions + priority + timeouts.
- Match: which packets does this rule apply to? (e.g., src MAC = AA:BB:CC:DD:EE:FF, in_port = 1)
- Action: what to do with matched packets? (e.g., output to port 2, flood, drop)
- Priority: higher number wins when multiple rules match
- Timeout: idle_timeout removes rule after N seconds of inactivity; hard_timeout removes it unconditionally

**What is SDN?**
Software-Defined Networking separates the control plane (what to do with traffic) from the data plane (actually forwarding traffic). The controller is the brain; switches are the muscle. OpenFlow is the protocol they speak.

**What happens without a controller?**
Switches flood all unknown packets. No learning occurs. No flow rules are installed. Traffic works but scales poorly (every packet hits all ports).

---

