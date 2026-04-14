#!/usr/bin/env python3
"""
test_scenarios.py
Automated test script for Port Status Monitoring Tool.

Scenario 1: Bring a link DOWN  → expect port DOWN alert in controller
Scenario 2: Bring the link UP  → expect port UP  alert in controller

Run this AFTER starting Ryu and topology in separate terminals.
Usage:
    sudo python3 test_scenarios.py
"""

import subprocess
import time
import sys


SWITCH = "s1"
# Interface names: s1-eth1 = link to h1, s1-eth2 = link to h2, etc.
IFACE = "s1-eth1"

SEPARATOR = "=" * 55


def run(cmd, desc=""):
    print(f"\n  >> {desc}")
    print(f"     CMD: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"     OUT: {result.stdout.strip()}")
    if result.returncode != 0 and result.stderr.strip():
        print(f"     ERR: {result.stderr.strip()}")
    return result


def ping_test(src_ip, dst_ip, count=3):
    """Ping between two IPs inside Mininet (using host namespace)."""
    result = subprocess.run(
        f"ping -c {count} -W 1 {dst_ip}",
        shell=True, capture_output=True, text=True
    )
    loss_line = [l for l in result.stdout.splitlines() if "packet loss" in l]
    print(f"     {loss_line[0] if loss_line else result.stdout.strip()}")
    return result.returncode == 0


def main():
    print(f"\n{SEPARATOR}")
    print("  PORT MONITOR - Automated Test Scenarios")
    print(SEPARATOR)

    # ── Scenario 1: Link DOWN ─────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print("  SCENARIO 1: Bring port DOWN")
    print(f"{'─'*55}")
    print(f"  Interface: {IFACE}")
    print("  Expected : Ryu controller logs a PORT DOWN event\n")

    run(f"sudo ip link set {IFACE} down", f"Taking {IFACE} DOWN")
    print("\n  Waiting 3 seconds for Ryu to detect the event...")
    time.sleep(3)

    # Verify interface is actually down
    run(f"ip link show {IFACE} | grep -o 'state [A-Z]*'",
        "Check interface state")

    # Check flow table
    run(f"sudo ovs-ofctl -O OpenFlow13 dump-ports {SWITCH}",
        "Dump OVS port stats")

    print("\n  CHECK YOUR RYU TERMINAL - you should see a DOWN alert ▼")
    print("  CHECK port_events.log - it should contain a DOWN entry")
    input("\n  Press ENTER to continue to Scenario 2...")

    # ── Scenario 2: Link UP ───────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print("  SCENARIO 2: Bring port back UP")
    print(f"{'─'*55}")
    print(f"  Interface: {IFACE}")
    print("  Expected : Ryu controller logs a PORT UP event\n")

    run(f"sudo ip link set {IFACE} up", f"Bringing {IFACE} UP")
    print("\n  Waiting 3 seconds for Ryu to detect the event...")
    time.sleep(3)

    run(f"ip link show {IFACE} | grep -o 'state [A-Z]*'",
        "Check interface state")
    run(f"sudo ovs-ofctl -O OpenFlow13 dump-ports {SWITCH}",
        "Dump OVS port stats after recovery")

    print("\n  CHECK YOUR RYU TERMINAL - you should see a UP alert ▲")
    print("  CHECK port_events.log - it should contain an UP entry")

    # ── Flow table dump ───────────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print("  BONUS: Flow table (for screenshots / Wireshark analysis)")
    print(f"{'─'*55}")
    run(f"sudo ovs-ofctl -O OpenFlow13 dump-flows {SWITCH}",
        "All flow rules in s1")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("  TEST SCENARIOS COMPLETE")
    print(SEPARATOR)
    print("  Screenshots to take for submission:")
    print("  1. Ryu terminal showing the DOWN alert")
    print("  2. Ryu terminal showing the UP  alert")
    print("  3. Contents of port_events.log")
    print("  4. Output of: sudo ovs-ofctl dump-flows s1")
    print("  5. Wireshark capture (optional but boosts marks)")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    if subprocess.run("which ovs-ofctl", shell=True,
                      capture_output=True).returncode != 0:
        print("ERROR: ovs-ofctl not found. Are you inside a Mininet environment?")
        sys.exit(1)
    main()
