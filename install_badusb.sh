#!/bin/bash
# install_badusb.sh - One-shot installer for Pi Zero 2 W BadUSB
# Run this ON the Pi: sudo bash install_badusb.sh
#
# What it does:
#   1. Creates ~/pi-badusb/ with all scripts
#   2. Makes everything executable
#   3. Sets up a root cron job to run autorun.sh at boot
#   4. Verifies /boot/firmware/config.txt and cmdline.txt are correct

set -e

INSTALL_DIR="/home/transient/pi-badusb"
BOOT_DIR=""

# Figure out where boot config lives (Bookworm vs older)
if [ -f /boot/firmware/config.txt ]; then
    BOOT_DIR="/boot/firmware"
elif [ -f /boot/config.txt ]; then
    BOOT_DIR="/boot"
else
    echo "ERROR: Cannot find config.txt in /boot/firmware/ or /boot/"
    exit 1
fi

echo "=== Pi Zero 2 W BadUSB Installer ==="
echo "Install dir: $INSTALL_DIR"
echo "Boot dir:    $BOOT_DIR"
echo ""

# --- Check boot config ---
echo "[1/5] Checking $BOOT_DIR/config.txt..."
if grep -q "dtoverlay=dwc2" "$BOOT_DIR/config.txt"; then
    echo "  OK: dtoverlay=dwc2 already present"
else
    echo "  ADDING: dtoverlay=dwc2"
    echo "dtoverlay=dwc2" >> "$BOOT_DIR/config.txt"
fi

echo "[2/5] Checking $BOOT_DIR/cmdline.txt..."
if grep -q "modules-load=dwc2,libcomposite" "$BOOT_DIR/cmdline.txt"; then
    echo "  OK: modules-load already present"
else
    echo "  ADDING: modules-load=dwc2,libcomposite after rootwait"
    sed -i 's/rootwait/rootwait modules-load=dwc2,libcomposite/' "$BOOT_DIR/cmdline.txt"
fi

# --- Create project directory ---
echo "[3/5] Creating $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# --- Copy scripts (they should be in the same dir as this installer) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for file in gadget_setup.sh autorun.sh ducky_parser.py test.payload.ds; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        cp "$SCRIPT_DIR/$file" "$INSTALL_DIR/$file"
        echo "  Copied: $file"
    else
        echo "  WARNING: $file not found in $SCRIPT_DIR"
    fi
done

chmod +x "$INSTALL_DIR"/*.sh
chmod +x "$INSTALL_DIR"/*.py
echo "  Permissions set"

# --- Set up root cron job ---
echo "[4/5] Setting up cron job..."
CRON_LINE="@reboot /bin/bash ${INSTALL_DIR}/autorun.sh &"

# Check if cron job already exists
if sudo crontab -l 2>/dev/null | grep -q "autorun.sh"; then
    echo "  OK: Cron job already exists"
else
    # Add to root's crontab
    (sudo crontab -l 2>/dev/null; echo "$CRON_LINE") | sudo crontab -
    echo "  Added: $CRON_LINE"
fi

# --- Verify ---
echo "[5/5] Verifying..."
echo ""
echo "  Boot config:"
grep "dwc2" "$BOOT_DIR/config.txt" | head -1 | sed 's/^/    /'
grep "modules-load" "$BOOT_DIR/cmdline.txt" | head -1 | sed 's/^/    /'
echo ""
echo "  Installed files:"
ls -la "$INSTALL_DIR/" | grep -v "^total" | sed 's/^/    /'
echo ""
echo "  Root crontab:"
sudo crontab -l 2>/dev/null | grep "autorun" | sed 's/^/    /'
echo ""
echo "=== Installation complete ==="
echo ""
echo "NEXT STEPS:"
echo "  1. Reboot:  sudo reboot"
echo "  2. After reboot, verify:  ls /dev/hidg0"
echo "  3. Edit your payload:  nano $INSTALL_DIR/test.payload.ds"
echo "  4. To test manually:   sudo python3 $INSTALL_DIR/ducky_parser.py $INSTALL_DIR/test.payload.ds"
echo ""
echo "ON BOOT: The Pi will automatically set up the gadget and wait"
echo "for a USB host connection, then fire the payload."
echo ""
echo "IMPORTANT: Plug the DATA port (middle micro-USB) into the target."
echo "Power can come from the target or separately via the end port."
