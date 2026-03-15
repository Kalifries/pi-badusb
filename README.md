# pi-badusb
------------------------------------------------------------------+++
||| Raspberry Pi Zero 2 W badusb setup with pentesting suite.     |||
------------------------------------------------------------------+++

 - Just run autorun.sh which will setup the pi and automate tasks to create your badusb. 
 The badusb has a ducky script parser so you can write in actual ducky script and create payloads.
 Once you create a payload you can load it into the web UI for easy access or just have it run
 once the badusb is plugged in.

         'python3 ~/pi-badusb/badusb-toggle.py' {boot-on/boot-off} {status} {start/stop}

 - running badusb-toggle allows you to switch between hid mode and regular pi mode at any time on
 demand. 

         'python3 ~/pi-badusb/payload_menu.py' (launches the web UI at your pi's IP port 8080)

 - There is a lot of room for expansion and tool integration that can match whatever you're wanting
 to acomplish.  I find that the pi zero 2 w is perfect for mobile pen-testing and when paired with 
 a wifi dongle, can go a long way. Add to it, create more, make this an amazing pen-testing pocket
 knife of your own!

 --tran$ient--


- __THIS PROJECT IS FOR LEARNING PURPOSES ONLY AND SHOULD NOT BE USED WITH ANY MALICIOUS INTENT. 
MAKE SURE YOU HAVE WRITTEN PERMISSION TO TEST ON THE NETWORK YOU ARE ON,  I AM NOT RESPONSIBLE 
FOR ANY MISUSE OF THIS PROJECT TO ENGAGE IN ILLEGAL ACTIVITIES.__





