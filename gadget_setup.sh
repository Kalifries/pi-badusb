#!/bin/bash
# gadget_setup.sh - Configure Pi Zero 2 W as USB HID keyboard
# The web menu runs over WiFi instead of USB ethernet.
# Must be run as root (sudo)
#
# Author: tran$ient

GADGET_DIR="/sys/kernel/config/usb_gadget/badusb"

# === CLEANUP ===
if [ -d "$GADGET_DIR" ]; then
    echo "[*] Cleaning up old gadget config..."
    echo "" > "${GADGET_DIR}/UDC" 2>/dev/null
    rm -f "${GADGET_DIR}/configs/c.1/hid.usb0"
    rm -f "${GADGET_DIR}/configs/c.1/acm.usb0"
    rm -f "${GADGET_DIR}/configs/c.1/ecm.usb0"
    rm -f "${GADGET_DIR}/configs/c.1/rndis.usb0"
    rmdir "${GADGET_DIR}/configs/c.1/strings/0x409" 2>/dev/null
    rmdir "${GADGET_DIR}/configs/c.1" 2>/dev/null
    rmdir "${GADGET_DIR}/functions/hid.usb0" 2>/dev/null
    rmdir "${GADGET_DIR}/functions/acm.usb0" 2>/dev/null
    rmdir "${GADGET_DIR}/functions/ecm.usb0" 2>/dev/null
    rmdir "${GADGET_DIR}/functions/rndis.usb0" 2>/dev/null
    rmdir "${GADGET_DIR}/strings/0x409" 2>/dev/null
    rmdir "${GADGET_DIR}" 2>/dev/null
fi

# === LOAD MODULE ===
/usr/sbin/modprobe libcomposite

# === CREATE GADGET ===
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# USB device descriptor
echo 0x1d6b > idVendor       # Linux Foundation
echo 0x0104 > idProduct      # Multifunction Composite Gadget
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

# Device strings
mkdir -p strings/0x409
echo "0123456789"           > strings/0x409/serialnumber
echo "Generic"              > strings/0x409/manufacturer
echo "USB Keyboard"         > strings/0x409/product

# Configuration
mkdir -p configs/c.1/strings/0x409
echo "Config 1" > configs/c.1/strings/0x409/configuration
echo 120        > configs/c.1/MaxPower

# === HID KEYBOARD ===
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 8 > functions/hid.usb0/report_length

echo -ne \\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0 > functions/hid.usb0/report_desc

# === LINK AND ACTIVATE ===
ln -s functions/hid.usb0 configs/c.1/
ls /sys/class/udc > UDC

echo ""
echo "=== Gadget Setup Complete ==="
echo ""

if [ -e /dev/hidg0 ]; then
    echo "[+] HID keyboard ready: /dev/hidg0"
else
    echo "[!] WARNING: /dev/hidg0 not found"
fi

# Show the Pi's WiFi IP for the web menu
WIFI_IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+')
if [ -n "$WIFI_IP" ]; then
    echo "[+] WiFi IP: ${WIFI_IP}"
    echo ""
    echo "To start the payload menu:"
    echo "  sudo python3 ~/badusb_menu/payload_menu.py"
    echo ""
    echo "Then open in browser:"
    echo "  http://${WIFI_IP}:8080"
else
    echo "[!] WiFi not connected - connect to WiFi first"
fi
