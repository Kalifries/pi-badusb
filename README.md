# pi-badusb

## Description
A BadUSB is a USB device that, when inserted into a host machine turns into a HID (Human Interface Device) gadget that injects pre-made customizable payloads with ducky script.

## Installation
Just run `install_badusb.sh` which will setup the pi and automate tasks to create your badusb. The badusb has a ducky script parser so you can write in actual ducky script and create payloads. Once you create a payload you can load it into the web UI for easy access or just have it run once the badusb is plugged in.

## Usage

### badusb-toggle
Switch between hid mode and regular pi mode at any time on demand.

```bash
python3 ~/pi-badusb/badusb-toggle.py {boot-on/boot-off} {status} {start/stop}
```

### payload_menu
Launch the web UI at your pi's IP port 8080.

```bash
python3 ~/pi-badusb/payload_menu.py
```

## Notes
There is a lot of room for expansion and tool integration that can match whatever you're wanting to accomplish.

## Legal Notice
**THIS PROJECT IS FOR LEARNING PURPOSES ONLY AND SHOULD NOT BE USED WITH ANY MALICIOUS INTENT. MAKE SURE YOU HAVE WRITTEN PERMISSION TO TEST ON THE NETWORK YOU ARE ON. I AM NOT RESPONSIBLE FOR ANY MISUSE OF THIS PROJECT TO ENGAGE IN ILLEGAL ACTIVITIES.**

---

--tran$ient--