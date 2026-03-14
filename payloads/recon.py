#!/usr/bin/env python3
"""
recon.py - Basic Reconnaissance Payload
Gathers system info from the machine the Pi is plugged into.

Every payload MUST have:
  - NAME (str)  - shows up in the menu
  - DESC (str)  - one-line description
  - run(io)     - the function that does the work

Author: tran$ient
"""

import subprocess

NAME = "System Recon"
DESC = "Grab hostname, OS, IP, and logged-in users"


def run(io):
    """
    Run recon commands and send output to io.
    io has .write() and .flush() - works with serial OR web.
    """
    commands = [
        ("HOSTNAME", "hostname"),
        ("OS INFO", "uname -a"),
        ("IP ADDR", "ip -brief addr"),
        ("USERS", "who"),
        ("UPTIME", "uptime"),
    ]

    for label, cmd in commands:
        io.write(f"\r\n  [{label}]\r\n")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout.strip()

            if output:
                for line in output.split("\n"):
                    io.write(f"  {line}\r\n")
            else:
                io.write("  (no output)\r\n")

        except subprocess.TimeoutExpired:
            io.write("  [!] Command timed out\r\n")
        except Exception as e:
            io.write(f"  [!] Error: {e}\r\n")

        io.flush()
