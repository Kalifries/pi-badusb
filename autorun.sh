#!/bin/bash
# autorun.sh - Sets up USB HID gadget and runs payload when connected to a host
# This script is meant to be called at boot via cron
# It waits for /dev/hidg0 to exist, then monitors for a USB host connection

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/autorun.log"
GADGET_SCRIPT="${SCRIPT_DIR}/gadget_setup.sh"
PAYLOAD_SCRIPT="${SCRIPT_DIR}/ducky_parser.py"
PAYLOAD_FILE="${SCRIPT_DIR}/test.payload.ds"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log "=== autorun.sh started ==="

# Step 1: Wait for boot to settle
sleep 10
log "Boot settle complete"

# Step 2: Run gadget setup
if [ ! -f "$GADGET_SCRIPT" ]; then
    log "ERROR: gadget_setup.sh not found at $GADGET_SCRIPT"
    exit 1
fi

log "Running gadget_setup.sh..."
bash "$GADGET_SCRIPT" >> "$LOG_FILE" 2>&1

# Step 3: Verify /dev/hidg0 exists
RETRIES=0
while [ ! -e /dev/hidg0 ]; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt 30 ]; then
        log "ERROR: /dev/hidg0 never appeared after 30 retries"
        exit 1
    fi
    log "Waiting for /dev/hidg0... (attempt $RETRIES)"
    sleep 2
done

log "/dev/hidg0 is ready"

# Step 4: Wait for USB host connection
# When the Pi is plugged into a target, the USB state changes.
# We check if we can write to hidg0 without getting an error.
log "Waiting for USB host connection..."

while true; do
    # Try writing an empty report (all zeros = no keys pressed)
    # If no host is connected, this will fail with BrokenPipeError
    if echo -ne '\x00\x00\x00\x00\x00\x00\x00\x00' > /dev/hidg0 2>/dev/null; then
        log "USB host detected!"
        break
    fi
    sleep 2
done

# Step 5: Small delay to let the target OS recognize the keyboard
sleep 3
log "Running payload: $PAYLOAD_FILE"

# Step 6: Run the payload
if [ ! -f "$PAYLOAD_FILE" ]; then
    log "ERROR: Payload file not found at $PAYLOAD_FILE"
    exit 1
fi

python3 "$PAYLOAD_SCRIPT" "$PAYLOAD_FILE" >> "$LOG_FILE" 2>&1
log "=== autorun.sh finished ==="
