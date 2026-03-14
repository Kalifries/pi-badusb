#!/usr/bin/env python3
"""
payload_menu.py - BadUSB Payload Menu System (Web Edition)
Runs on Raspberry Pi Zero 2 W over WiFi.
Serves an interactive web menu so you can pick and fire
payloads from any browser on your network.

Safe mode: does NOTHING until you explicitly select a payload.

No external dependencies - uses Python's built-in http.server.

Author: tran$ient
"""

import os
import sys
import json
import time
import threading
import importlib.util
import io as stdio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs


# === CONFIGURATION ===

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_DIR = os.path.join(BASE_DIR, "payloads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Web server settings
HOST = "0.0.0.0"   # Listen on all interfaces
PORT = 8080


# === HELPER FUNCTIONS ===

def load_config():
    """Load settings from config.json, create defaults if missing."""
    default_config = {
        "banner_text": "tran$ient // payload menu",
        "log_enabled": True,
        "safe_mode": True
    }

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    else:
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)
        return default_config


def ensure_dirs():
    """Make sure required directories exist."""
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)


def log_event(message):
    """Write a timestamped line to the log file."""
    log_file = os.path.join(LOG_DIR, "payload.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"

    with open(log_file, "a") as f:
        f.write(line)

    # Also print to Pi's terminal so you can see what's happening
    print(f"  {line.strip()}")


def discover_payloads():
    """
    Scan payloads/ for .py files with NAME, DESC, and run().
    Returns a list of payload info dicts.
    """
    payloads = []

    if not os.path.isdir(PAYLOAD_DIR):
        return payloads

    for filename in sorted(os.listdir(PAYLOAD_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        filepath = os.path.join(PAYLOAD_DIR, filename)

        try:
            spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "NAME") and hasattr(module, "run"):
                payloads.append({
                    "name": module.NAME,
                    "desc": getattr(module, "DESC", "No description"),
                    "file": filename,
                    "module": module
                })
        except Exception as e:
            log_event(f"ERROR loading {filename}: {e}")

    return payloads


def get_log_entries(count=30):
    """Return the last N log entries as a list of strings."""
    log_file = os.path.join(LOG_DIR, "payload.log")

    if not os.path.exists(log_file):
        return ["(no log entries yet)"]

    with open(log_file, "r") as f:
        lines = f.readlines()

    return [line.strip() for line in lines[-count:]]


# === OUTPUT CAPTURE ===

class OutputCapture:
    """
    Captures payload output so we can display it in the browser.

    Payloads call io.write() and io.flush() just like before.
    Instead of going to a serial port, the text gets stored
    in a list. After the payload runs, we grab all the output
    and send it back as HTML.

    This means your existing payloads (recon.py, net_scan.py)
    work WITHOUT any changes. Same interface, different backend.
    """

    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass  # nothing to flush, it's all in memory

    def readline(self):
        return ""  # payloads don't read input in web mode

    def get_output(self):
        """Return all captured text as one string."""
        return "".join(self.lines)


# === HTML TEMPLATES ===

def render_page(config, payloads, message="", output="", log_entries=None):
    """
    Build the full HTML page.

    Instead of an external template file, the HTML is right here
    so the whole menu is a single .py file + payloads folder.
    No dependencies, no template engines, nothing to install.
    """
    banner = config.get("banner_text", "PAYLOAD MENU")

    # Build payload buttons
    payload_html = ""
    if not payloads:
        payload_html = '<div class="empty">No payloads found in payloads/ directory</div>'
    else:
        for i, p in enumerate(payloads):
            payload_html += f'''
            <div class="payload-card">
                <div class="payload-info">
                    <span class="payload-name">{p["name"]}</span>
                    <span class="payload-desc">{p["desc"]}</span>
                    <span class="payload-file">{p["file"]}</span>
                </div>
                <form method="POST" action="/run">
                    <input type="hidden" name="index" value="{i}">
                    <button type="submit" class="run-btn">EXECUTE</button>
                </form>
            </div>'''

    # Build message area (shows after running a payload)
    message_html = ""
    if message:
        message_html = f'<div class="message">{message}</div>'

    # Build output area
    output_html = ""
    if output:
        # Escape HTML and preserve formatting
        safe_output = (output
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
        output_html = f'<div class="output-box"><pre>{safe_output}</pre></div>'

    # Build log area
    log_html = ""
    if log_entries:
        log_lines = "\n".join(log_entries)
        log_html = f'<div class="output-box"><pre>{log_lines}</pre></div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{banner}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: #0a0a0a;
            color: #00ff41;
            font-family: 'Share Tech Mono', 'Courier New', monospace;
            min-height: 100vh;
            padding: 20px;
        }}

        .scanline {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0, 255, 65, 0.03) 2px,
                rgba(0, 255, 65, 0.03) 4px
            );
            z-index: 999;
        }}

        .container {{
            max-width: 700px;
            margin: 0 auto;
        }}

        .banner {{
            border: 1px solid #00ff41;
            padding: 15px 20px;
            margin-bottom: 20px;
            text-align: center;
        }}

        .banner h1 {{
            font-size: 1.4em;
            font-weight: normal;
            letter-spacing: 2px;
        }}

        .safe-mode {{
            color: #ffaa00;
            font-size: 0.85em;
            margin-top: 8px;
            letter-spacing: 1px;
        }}

        .nav {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}

        .nav a {{
            color: #00ff41;
            text-decoration: none;
            border: 1px solid #333;
            padding: 8px 16px;
            font-family: inherit;
            font-size: 0.85em;
            transition: all 0.2s;
        }}

        .nav a:hover {{
            background: #00ff41;
            color: #0a0a0a;
        }}

        .section-label {{
            color: #666;
            font-size: 0.8em;
            margin-bottom: 10px;
            letter-spacing: 2px;
        }}

        .payload-card {{
            border: 1px solid #1a1a1a;
            padding: 15px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: border-color 0.2s;
        }}

        .payload-card:hover {{
            border-color: #00ff41;
        }}

        .payload-info {{
            display: flex;
            flex-direction: column;
            gap: 3px;
        }}

        .payload-name {{
            color: #00ff41;
            font-size: 1em;
        }}

        .payload-desc {{
            color: #888;
            font-size: 0.8em;
        }}

        .payload-file {{
            color: #444;
            font-size: 0.7em;
        }}

        .run-btn {{
            background: transparent;
            color: #ff3333;
            border: 1px solid #ff3333;
            padding: 8px 20px;
            font-family: inherit;
            font-size: 0.85em;
            cursor: pointer;
            letter-spacing: 2px;
            transition: all 0.2s;
        }}

        .run-btn:hover {{
            background: #ff3333;
            color: #0a0a0a;
        }}

        .message {{
            background: #111;
            border-left: 3px solid #00ff41;
            padding: 12px 16px;
            margin-bottom: 15px;
            font-size: 0.85em;
        }}

        .output-box {{
            background: #050505;
            border: 1px solid #1a1a1a;
            padding: 15px;
            margin-bottom: 20px;
            max-height: 400px;
            overflow-y: auto;
        }}

        .output-box pre {{
            font-family: inherit;
            font-size: 0.8em;
            color: #aaa;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .empty {{
            color: #666;
            padding: 20px;
            text-align: center;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 15px;
            border-top: 1px solid #1a1a1a;
            color: #333;
            font-size: 0.7em;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container">
        <div class="banner">
            <h1>{banner}</h1>
            <div class="safe-mode">[SAFE MODE] select payload to execute</div>
        </div>

        <div class="nav">
            <a href="/">MENU</a>
            <a href="/reload">RELOAD</a>
            <a href="/log">LOG</a>
        </div>

        {message_html}
        {output_html}
        {log_html}

        <div class="section-label">AVAILABLE PAYLOADS</div>
        {payload_html}

        <div class="footer">
            tran$ient // badusb toolkit // safe mode active
        </div>
    </div>
</body>
</html>'''


# === WEB SERVER ===

class PayloadHandler(BaseHTTPRequestHandler):
    """
    Handles HTTP requests for the payload menu.

    GET /         - show the menu
    GET /reload   - rescan payloads folder
    GET /log      - show recent log entries
    POST /run     - execute a payload

    This is a class that inherits from BaseHTTPRequestHandler.
    Python's http.server calls do_GET() when a GET request comes in,
    and do_POST() for POST requests. We override those methods
    to serve our menu.
    """

    # Class-level variables shared across all requests.
    # These get set in main() before the server starts.
    payloads = []
    config = {}
    lock = threading.Lock()  # prevents two payloads running at once

    def do_GET(self):
        """Handle GET requests."""

        if self.path == "/":
            # Main menu page
            html = render_page(self.config, self.payloads)
            self.send_html(html)

        elif self.path == "/reload":
            # Rescan the payloads directory
            PayloadHandler.payloads = discover_payloads()
            count = len(self.payloads)
            log_event(f"RELOAD: {count} payload(s) found")
            html = render_page(
                self.config, self.payloads,
                message=f"Reloaded: {count} payload(s) found"
            )
            self.send_html(html)

        elif self.path == "/log":
            # Show log entries
            entries = get_log_entries(30)
            html = render_page(
                self.config, self.payloads,
                log_entries=entries
            )
            self.send_html(html)

        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests (payload execution)."""

        if self.path == "/run":
            # Read the form data
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = parse_qs(body)

            # Get the payload index
            index_str = params.get("index", [""])[0]

            try:
                index = int(index_str)
            except ValueError:
                self.send_html(render_page(
                    self.config, self.payloads,
                    message="Invalid payload selection"
                ))
                return

            if index < 0 or index >= len(self.payloads):
                self.send_html(render_page(
                    self.config, self.payloads,
                    message=f"Payload index {index} out of range"
                ))
                return

            payload = self.payloads[index]
            name = payload["name"]

            # Use the lock so only one payload runs at a time
            if not self.lock.acquire(blocking=False):
                self.send_html(render_page(
                    self.config, self.payloads,
                    message="Another payload is already running. Wait for it to finish."
                ))
                return

            try:
                log_event(f"EXECUTE: {name} ({payload['file']})")

                # Create an output capture object
                # This has the same .write()/.flush() interface
                # that serial payloads expect
                capture = OutputCapture()
                start_time = time.time()

                # Run the payload
                payload["module"].run(capture)
                elapsed = round(time.time() - start_time, 2)

                log_event(f"SUCCESS: {name} completed in {elapsed}s")

                # Build the response with captured output
                output = capture.get_output()
                self.send_html(render_page(
                    self.config, self.payloads,
                    message=f"Executed: {name} ({elapsed}s)",
                    output=output
                ))

            except Exception as e:
                elapsed = round(time.time() - start_time, 2)
                log_event(f"FAILED: {name} after {elapsed}s - {e}")

                self.send_html(render_page(
                    self.config, self.payloads,
                    message=f"FAILED: {name} - {e}"
                ))

            finally:
                self.lock.release()

        else:
            self.send_error(404)

    def send_html(self, html):
        """Send an HTML response."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        """
        Override the default request logging.
        BaseHTTPRequestHandler prints every request to stderr.
        We redirect it to our own log format.
        """
        pass  # suppress default logging, we do our own


# === MAIN ===

def main():
    """Start the web-based payload menu."""
    ensure_dirs()
    config = load_config()

    log_event("MENU STARTED - web mode - safe mode active")

    # Discover payloads
    payloads = discover_payloads()
    log_event(f"DISCOVERED {len(payloads)} payload(s)")

    # Set class-level variables so the handler can access them
    PayloadHandler.payloads = payloads
    PayloadHandler.config = config

    # Start the web server
    server = HTTPServer((HOST, PORT), PayloadHandler)

    # Detect WiFi IP so we can show the correct URL
    import subprocess
    try:
        result = subprocess.run(
            "ip -4 addr show wlan0 | grep -oP '(?<=inet\\s)\\d+\\.\\d+\\.\\d+\\.\\d+'",
            shell=True, capture_output=True, text=True
        )
        wifi_ip = result.stdout.strip() or "?.?.?.?"
    except Exception:
        wifi_ip = "?.?.?.?"

    print("")
    print("  +------------------------------------------+")
    print(f"  |  tran$ient // payload menu               |")
    print("  +------------------------------------------+")
    print(f"  |  Web server running on port {PORT}         |")
    print(f"  |  Open http://{wifi_ip}:{PORT}{' ' * (14 - len(wifi_ip))}|")
    print(f"  |  Payloads loaded: {len(payloads):<23}|")
    print("  +------------------------------------------+")
    print("")
    print("  [*] Waiting for connections...")
    print("  [*] Press Ctrl+C to stop")
    print("")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  [*] Shutting down. Stay dangerous.")
        log_event("MENU SHUTDOWN")
        server.shutdown()


if __name__ == "__main__":
    main()
