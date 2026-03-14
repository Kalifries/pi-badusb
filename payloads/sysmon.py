#!/usr/bin/env python3

import subprocess
import os

#  --- FUNCTIONS ----------------------------------------------------------------------------------

def get_cpu_usage():
    # Read /proc/stat twice to calculate CPU usage over 1 second
    with open("/proc/stat") as f:
        line1 = f.readline().split()

    import time
    time.sleep(1)

    with open("/proc/stat") as f:
        line2 = f.readline().split()

    # The number after 'cpu' are: user, nice, system, idle, iowait, irq, softirq
    idle1 = int(line1[4])
    total1 = sum(int(x) for x in line1[1:])
    idle2 = int(line2[4])
    total2 = sum(int(x) for x in line2[1:])

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    usage = 100 * (1 - idle_delta / total_delta)
    return round(usage, 1)


def get_ram_usage():
    with open("/proc/meminfo") as f:
        lines = f.readlines()

    # Pull out the values we need
    mem = {}
    for line in lines:
        parts = line.split()
        mem [parts[0]] = int(parts[1])  # value is in kB

    total = mem["MemTotal:"]
    available = mem["MemAvailable:"]
    used = total - available
    percent = round((used / total) * 100, 1)

    # Convert kB to GB
    total_gb = round(total / 1024 / 1024, 2)
    used_gb = round(used / 1024 / 1024, 2)

    return used_gb, total_gb, percent


def get_disk_usage(path="/home"):
    result = subprocess.run(
            ["df", "-h", path],
            capture_output=True,
            text=True
    )
    lines = result.stdout.strip().split("\n")
    parts = lines[1].split()
    # df -h output: Filesystem, Size, Used, Avail, Use%, Mounted on
    return parts[1], parts[2], parts[4]    # total, used, percent


def get_top_processes(n=10):
    result = subprocess.run(
            ["ps", "aux", "--sort=-%cpu"],
            capture_output=True,
            text=True
            )
    lines = result.stdout.strip().split("\n")
    # First line is the header, then take top n
    header = lines[0]
    top = lines[1:n+1]
    return top
# --- MAIN ----------------------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("       SYSTEM HEALTH MONITOR")
    print("=" * 50)

    print("\n CPU Usage (sampling 1 second)...")
    cpu = get_cpu_usage()
    cpu_bar = "|" * int(cpu // 5) + "-" * (20 - int(cpu // 5))
    print(f"    CPU: [{cpu_bar}] {cpu}%")

    print("\n RAM Usage:")
    used_gb, total_gb, ram_percent = get_ram_usage()
    ram_bar = "|" * int(ram_percent // 5) + "-" * (20 - int(ram_percent // 5))
    print(f"    RAM: [{ram_bar}] {ram_percent}% ({used_gb}GB / {total_gb}GB)")

    print("\n Disk Usage (/):")
    total, used, percent = get_disk_usage()
    print(f"    Disk: {used} used of {total} ({percent})")

    print(f"\n Top 10 Processes by CPU:")
    for proc in get_top_processes():
        # Columns: USER, PID, %CPU, %MEM, ... COMMAND
        parts = proc.split()
        if len(parts) >= 11:
            print(f"    {parts[10][:25]:<25} CPU: {parts[2]}% MEM: {parts[3]}%")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
