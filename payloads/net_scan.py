#!/usr/bin/env python3
"""
net_scan.py - Quick Network Scan Payload
Maps the local network via ARP table.

Author: tran$ient
"""

import subprocess

NAME = "Network Scan"
DESC = "ARP table dump - find devices on the local network"


def run(io):
    """Grab the ARP table and display it."""
    io.write("\r\n  [*] Dumping ARP table...\r\n")
    io.flush()

    try:
        result = subprocess.run(
            "ip neigh show",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        lines = result.stdout.strip().split("\n")

        if lines and lines[0]:
            io.write(f"\r\n  Found {len(lines)} neighbor(s):\r\n")
            io.write(f"  {'=' * 40}\r\n")

            for line in lines:
                io.write(f"  {line}\r\n")
        else:
            io.write("  [!] ARP table empty\r\n")

    except subprocess.TimeoutExpired:
        io.write("  [!] Scan timed out\r\n")
    except Exception as e:
        io.write(f"  [!] Error: {e}\r\n")

    io.flush()
