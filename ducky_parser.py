#!/usr/bin/env python3
"""
ducky_parser.py - Ducky Script parser for Pi Zero 2 W BadUSB
Reads .ds payload files and sends HID keyboard reports via /dev/hidg0

Usage: sudo python3 ducky_parser.py payload.ds
"""

import time
import sys
import os
import logging

# --- Configuration ---
HID_DEVICE = '/dev/hidg0'
DEFAULT_DELAY = 0          # ms delay between commands (0 = none)
DEFAULT_CHAR_DELAY = 0.01  # seconds between keystrokes

# --- Logging ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ducky.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('ducky')

# --- HID Keycodes (US keyboard layout) ---
# Standard characters - no modifier needed
KEY_CODES = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08,
    'f': 0x09, 'g': 0x0a, 'h': 0x0b, 'i': 0x0c, 'j': 0x0d,
    'k': 0x0e, 'l': 0x0f, 'm': 0x10, 'n': 0x11, 'o': 0x12,
    'p': 0x13, 'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17,
    'u': 0x18, 'v': 0x19, 'w': 0x1a, 'x': 0x1b, 'y': 0x1c,
    'z': 0x1d, '1': 0x1e, '2': 0x1f, '3': 0x20, '4': 0x21,
    '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26,
    '0': 0x27, ' ': 0x2c, '-': 0x2d, '=': 0x2e, '[': 0x2f,
    ']': 0x30, '\\': 0x31, ';': 0x33, "'": 0x34, '`': 0x35,
    ',': 0x36, '.': 0x37, '/': 0x38,
}

# Characters that require SHIFT to be held
SHIFT_CHARS = {
    '!': 0x1e, '@': 0x1f, '#': 0x20, '$': 0x21, '%': 0x22,
    '^': 0x23, '&': 0x24, '*': 0x25, '(': 0x26, ')': 0x27,
    '_': 0x2d, '+': 0x2e, '{': 0x2f, '}': 0x30, '|': 0x31,
    ':': 0x33, '"': 0x34, '~': 0x35, '<': 0x36, '>': 0x37,
    '?': 0x38,
}

# Modifier keys (bitmask - can be combined with |)
MODIFIER_CODES = {
    'CTRL':    0x01,
    'CONTROL': 0x01,
    'SHIFT':   0x02,
    'ALT':     0x04,
    'GUI':     0x08,
    'WINDOWS': 0x08,
    'SUPER':   0x08,
    'COMMAND': 0x08,
}

# Special (non-printable) keys
SPECIAL_KEYS = {
    'ENTER':      0x28,
    'RETURN':     0x28,
    'ESCAPE':     0x29,
    'ESC':        0x29,
    'BACKSPACE':  0x2a,
    'TAB':        0x2b,
    'SPACE':      0x2c,
    'CAPSLOCK':   0x39,
    'F1':  0x3a, 'F2':  0x3b, 'F3':  0x3c, 'F4':  0x3d,
    'F5':  0x3e, 'F6':  0x3f, 'F7':  0x40, 'F8':  0x41,
    'F9':  0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,
    'PRINTSCREEN': 0x46,
    'SCROLLLOCK':  0x47,
    'PAUSE':       0x48,
    'INSERT':      0x49,
    'HOME':        0x4a,
    'PAGEUP':      0x4b,
    'DELETE':      0x4c,
    'END':         0x4d,
    'PAGEDOWN':    0x4e,
    'RIGHT':       0x4f, 'RIGHTARROW': 0x4f,
    'LEFT':        0x50, 'LEFTARROW':  0x50,
    'DOWN':        0x51, 'DOWNARROW':  0x51,
    'UP':          0x52, 'UPARROW':    0x52,
    'NUMLOCK':     0x53,
    'APP':         0x65,
    'MENU':        0x65,
}


def send_report(modifier, keycode):
    """
    Send an 8-byte HID keyboard report to the target.
    Byte layout: [modifier, reserved, key1, key2, key3, key4, key5, key6]
    Then send an empty report to "release" the key.
    """
    try:
        with open(HID_DEVICE, 'rb+') as f:
            # Press
            f.write(bytes([modifier, 0, keycode, 0, 0, 0, 0, 0]))
            f.flush()
            time.sleep(DEFAULT_CHAR_DELAY)
            # Release
            f.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            f.flush()
            time.sleep(DEFAULT_CHAR_DELAY)
    except FileNotFoundError:
        log.error(f"/dev/hidg0 not found - is gadget_setup.sh running?")
        sys.exit(1)
    except BrokenPipeError:
        log.error("BrokenPipe - Pi not connected to a target host via USB data port")
        sys.exit(1)
    except Exception as e:
        log.error(f"HID write error: {e}")
        sys.exit(1)


def type_string(text):
    """Type a string one character at a time, handling shift for uppercase and symbols."""
    for char in text:
        lower = char.lower()
        if char in SHIFT_CHARS:
            send_report(0x02, SHIFT_CHARS[char])
        elif lower in KEY_CODES:
            modifier = 0x02 if char.isupper() else 0x00
            send_report(modifier, KEY_CODES[lower])
        elif char == '\n':
            send_report(0, SPECIAL_KEYS['ENTER'])
        elif char == '\t':
            send_report(0, SPECIAL_KEYS['TAB'])
        else:
            log.warning(f"Unknown char: '{char}' (U+{ord(char):04X}) - skipped")


def parse_and_run(filepath):
    """Parse a Ducky Script file and execute each command."""
    log.info(f"--- Payload start: {filepath} ---")

    if not os.path.exists(filepath):
        log.error(f"Payload file not found: {filepath}")
        sys.exit(1)

    if not os.path.exists(HID_DEVICE):
        log.error(f"{HID_DEVICE} not found - run gadget_setup.sh first")
        sys.exit(1)

    with open(filepath, 'r') as f:
        lines = f.readlines()

    default_delay = 0

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('REM') or line.startswith('//'):
            continue

        parts = line.split(' ', 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ''

        log.info(f"Line {line_num}: {cmd} {arg[:50]}")

        try:
            # --- Timing commands ---
            if cmd == 'DELAY':
                time.sleep(int(arg) / 1000)

            elif cmd == 'DEFAULT_DELAY' or cmd == 'DEFAULTDELAY':
                default_delay = int(arg)

            # --- String typing ---
            elif cmd == 'STRING':
                type_string(arg)

            elif cmd == 'STRINGLN':
                type_string(arg)
                send_report(0, SPECIAL_KEYS['ENTER'])

            # --- Special keys as standalone commands ---
            elif cmd in SPECIAL_KEYS:
                send_report(0, SPECIAL_KEYS[cmd])

            # --- GUI/Windows key combos ---
            elif cmd == 'GUI' or cmd == 'WINDOWS' or cmd == 'SUPER':
                if arg.upper() in SPECIAL_KEYS:
                    send_report(MODIFIER_CODES['GUI'], SPECIAL_KEYS[arg.upper()])
                elif arg.lower() in KEY_CODES:
                    send_report(MODIFIER_CODES['GUI'], KEY_CODES[arg.lower()])
                else:
                    send_report(MODIFIER_CODES['GUI'], 0)

            # --- Modifier combos (CTRL c, CTRL ALT DELETE, etc.) ---
            elif cmd in MODIFIER_CODES:
                tokens = line.upper().split()
                modifier = 0
                keycode = 0
                for token in tokens:
                    if token in MODIFIER_CODES:
                        modifier |= MODIFIER_CODES[token]
                    elif token in SPECIAL_KEYS:
                        keycode = SPECIAL_KEYS[token]
                    elif token.lower() in KEY_CODES:
                        keycode = KEY_CODES[token.lower()]
                send_report(modifier, keycode)

            # --- Repeat last command ---
            elif cmd == 'REPEAT' or cmd == 'REPLAY':
                log.warning(f"REPEAT not implemented yet - skipped")

            else:
                log.warning(f"Unknown command on line {line_num}: {cmd}")

        except ValueError as e:
            log.error(f"Bad value on line {line_num}: {line} -> {e}")
        except Exception as e:
            log.error(f"Error on line {line_num}: {line} -> {e}")
            raise

        # Apply default delay between commands
        if default_delay > 0:
            time.sleep(default_delay / 1000)

    log.info(f"--- Payload complete: {filepath} ---")
    print(f"Payload executed successfully. Log: {LOG_FILE}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: sudo python3 ducky_parser.py <payload.ds>")
        print("       sudo python3 ducky_parser.py test.payload.ds")
        sys.exit(1)

    parse_and_run(sys.argv[1])
