#!/bin/bash
# badusb-toggle.sh — Live toggle for BadUSB gadget mode on Pi Zero 2 W
# No reboot required. Tears down or sets up the gadget in real time.
#
# Usage:
#   sudo ./badusb-toggle.sh start    — Activate BadUSB (gadget + autorun)
#   sudo ./badusb-toggle.sh stop     — Deactivate BadUSB immediately
#   sudo ./badusb-toggle.sh status   — Show current state
#   sudo ./badusb-toggle.sh boot-on  — Enable autorun at boot via cron
#   sudo ./badusb-toggle.sh boot-off — Disable autorun at boot (keeps cron entry commented)

# --- Config ---
SCRIPT_DIR="/home/transient/pi-badusb"
GADGET_DIR="/sys/kernel/config/usb_gadget/badusb"
GADGET_SCRIPT="${SCRIPT_DIR}/gadget_setup.sh"
AUTORUN_SCRIPT="${SCRIPT_DIR}/autorun.sh"
CRON_MARKER="# BADUSB AUTORUN"

# --- Must be root ---
if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo:  sudo ./badusb-toggle.sh [start|stop|status]"
    exit 1
fi

# --- Functions ---

do_stop() {
    echo "=== Stopping BadUSB ==="
    echo ""

    # Step 1: Kill autorun.sh if it's running
    AUTORUN_PIDS=$(pgrep -f "autorun.sh" 2>/dev/null)
    if [[ -n "$AUTORUN_PIDS" ]]; then
        echo "[1/4] Killing autorun.sh (PIDs: $AUTORUN_PIDS)..."
        kill $AUTORUN_PIDS 2>/dev/null
        sleep 1
        # Force kill if still alive
        AUTORUN_PIDS=$(pgrep -f "autorun.sh" 2>/dev/null)
        if [[ -n "$AUTORUN_PIDS" ]]; then
            kill -9 $AUTORUN_PIDS 2>/dev/null
            echo "       Force killed stubborn process"
        fi
        echo "       Done"
    else
        echo "[1/4] autorun.sh not running — skipping"
    fi

    # Step 2: Kill any running ducky_parser.py
    DUCKY_PIDS=$(pgrep -f "ducky_parser.py" 2>/dev/null)
    if [[ -n "$DUCKY_PIDS" ]]; then
        echo "[2/4] Killing ducky_parser.py (PIDs: $DUCKY_PIDS)..."
        kill $DUCKY_PIDS 2>/dev/null
        sleep 1
        kill -9 $(pgrep -f "ducky_parser.py" 2>/dev/null) 2>/dev/null
        echo "       Done"
    else
        echo "[2/4] ducky_parser.py not running — skipping"
    fi

    # Step 3: Tear down the live gadget in ConfigFS
    if [[ -d "$GADGET_DIR" ]]; then
        echo "[3/4] Tearing down USB gadget..."

        # Disable the gadget (disconnect from UDC)
        echo "" > "${GADGET_DIR}/UDC" 2>/dev/null

        # Unlink function from config
        rm -f "${GADGET_DIR}/configs/c.1/hid.usb0" 2>/dev/null

        # Remove strings and directories (order matters)
        rmdir "${GADGET_DIR}/configs/c.1/strings/0x409" 2>/dev/null
        rmdir "${GADGET_DIR}/configs/c.1" 2>/dev/null
        rmdir "${GADGET_DIR}/functions/hid.usb0" 2>/dev/null
        rmdir "${GADGET_DIR}/strings/0x409" 2>/dev/null
        rmdir "${GADGET_DIR}" 2>/dev/null

        if [[ ! -d "$GADGET_DIR" ]]; then
            echo "       Gadget removed"
        else
            echo "       WARNING: Could not fully remove gadget dir"
        fi
    else
        echo "[3/4] No gadget configured — skipping"
    fi

    # Step 4: Unload libcomposite
    if lsmod | grep -q "^libcomposite"; then
        echo "[4/4] Unloading libcomposite module..."
        modprobe -r libcomposite 2>/dev/null
        if lsmod | grep -q "^libcomposite"; then
            echo "       WARNING: Could not unload (something may still be using it)"
        else
            echo "       Done"
        fi
    else
        echo "[4/4] libcomposite not loaded — skipping"
    fi

    echo ""
    if [[ -e /dev/hidg0 ]]; then
        echo "WARNING: /dev/hidg0 still exists. Something didn't clean up right."
    else
        echo "BadUSB is OFF. /dev/hidg0 is gone. Pi is in normal mode."
    fi
    echo ""
}

do_start() {
    echo "=== Starting BadUSB ==="
    echo ""

    # Check if already running
    if [[ -e /dev/hidg0 ]]; then
        echo "BadUSB is already active (/dev/hidg0 exists)."
        echo "Run 'sudo ./badusb-toggle.sh stop' first if you want to restart it."
        exit 0
    fi

    # Step 1: Run gadget setup
    if [[ ! -f "$GADGET_SCRIPT" ]]; then
        echo "ERROR: gadget_setup.sh not found at $GADGET_SCRIPT"
        exit 1
    fi

    echo "[1/2] Setting up USB gadget..."
    bash "$GADGET_SCRIPT"

    if [[ ! -e /dev/hidg0 ]]; then
        echo "ERROR: /dev/hidg0 did not appear after gadget setup"
        exit 1
    fi
    echo "       /dev/hidg0 is live"

    # Step 2: Launch autorun in background
    echo "[2/2] Launching autorun.sh in background..."
    nohup bash "$AUTORUN_SCRIPT" > /dev/null 2>&1 &
    echo "       PID: $!"

    echo ""
    echo "BadUSB is ON. Gadget is active and autorun is waiting for a host."
    echo ""
}

do_status() {
    echo "=== BadUSB Status ==="
    echo ""

    # hidg0
    if [[ -e /dev/hidg0 ]]; then
        echo "[gadget]   /dev/hidg0 EXISTS — gadget is configured"
    else
        echo "[gadget]   /dev/hidg0 does NOT exist — gadget is down"
    fi

    # ConfigFS
    if [[ -d "$GADGET_DIR" ]]; then
        echo "[configfs] $GADGET_DIR exists"
        UDC_CONTENT=$(cat "${GADGET_DIR}/UDC" 2>/dev/null)
        if [[ -n "$UDC_CONTENT" ]]; then
            echo "[configfs] Bound to UDC: $UDC_CONTENT"
        else
            echo "[configfs] NOT bound to any UDC"
        fi
    else
        echo "[configfs] No gadget directory — clean"
    fi

    # libcomposite
    if lsmod | grep -q "^libcomposite"; then
        echo "[module]   libcomposite is LOADED"
    else
        echo "[module]   libcomposite is NOT loaded"
    fi

    # dwc2
    if lsmod | grep -q "^dwc2"; then
        echo "[module]   dwc2 is LOADED"
    else
        echo "[module]   dwc2 is NOT loaded"
    fi

    # autorun.sh process
    AUTORUN_PIDS=$(pgrep -f "autorun.sh" 2>/dev/null)
    if [[ -n "$AUTORUN_PIDS" ]]; then
        echo "[process]  autorun.sh is RUNNING (PIDs: $AUTORUN_PIDS)"
    else
        echo "[process]  autorun.sh is NOT running"
    fi

    # ducky_parser.py process
    DUCKY_PIDS=$(pgrep -f "ducky_parser.py" 2>/dev/null)
    if [[ -n "$DUCKY_PIDS" ]]; then
        echo "[process]  ducky_parser.py is RUNNING (PIDs: $DUCKY_PIDS)"
    else
        echo "[process]  ducky_parser.py is NOT running"
    fi

    # Boot cron
    if crontab -l 2>/dev/null | grep -v "^#" | grep -q "autorun.sh"; then
        echo "[boot]     Autorun at boot is ENABLED"
    elif crontab -l 2>/dev/null | grep "^#.*autorun.sh" | grep -q "autorun.sh"; then
        echo "[boot]     Autorun at boot is DISABLED (commented out)"
    else
        echo "[boot]     No cron entry found for autorun"
    fi

    echo ""
}

do_boot_on() {
    echo "=== Enabling BadUSB at boot ==="

    # Check if there's already an active cron entry
    if crontab -l 2>/dev/null | grep -v "^#" | grep -q "autorun.sh"; then
        echo "Already enabled."
        return
    fi

    # Check if there's a commented-out entry to uncomment
    if crontab -l 2>/dev/null | grep "^#.*autorun.sh" | grep -q "autorun.sh"; then
        crontab -l 2>/dev/null | sed "s|^#\(.*autorun.sh.*\)|\1|" | crontab -
        echo "Uncommented existing cron entry."
    else
        # Add a new one
        (crontab -l 2>/dev/null; echo "@reboot /bin/bash ${AUTORUN_SCRIPT} ${CRON_MARKER}") | crontab -
        echo "Added cron entry for autorun at boot."
    fi

    echo "BadUSB will start automatically on next reboot."
    echo ""
}

do_boot_off() {
    echo "=== Disabling BadUSB at boot ==="

    if ! crontab -l 2>/dev/null | grep -v "^#" | grep -q "autorun.sh"; then
        echo "Already disabled (no active cron entry)."
        return
    fi

    # Comment out the cron entry instead of deleting it
    crontab -l 2>/dev/null | sed "s|^\(.*autorun.sh.*\)|#\1|" | crontab -
    echo "Commented out cron entry. BadUSB will NOT start on boot."
    echo "Run 'sudo ./badusb-toggle.sh boot-on' to re-enable."
    echo ""
}

# --- Main ---
case "${1,,}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    boot-on)
        do_boot_on
        ;;
    boot-off)
        do_boot_off
        ;;
    *)
        echo "badusb-toggle.sh — Live BadUSB mode control (no reboot needed)"
        echo ""
        echo "Usage: sudo ./badusb-toggle.sh <command>"
        echo ""
        echo "  start    — Activate gadget + autorun NOW"
        echo "  stop     — Kill everything and remove gadget NOW"
        echo "  status   — Show what's running"
        echo "  boot-on  — Enable autorun at boot (cron)"
        echo "  boot-off — Disable autorun at boot (cron)"
        exit 1
        ;;
esac
