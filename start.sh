#!/bin/sh
sudo pigpiod
cd /home/pavtiger/Docs/remote-joystick-control/; /usr/bin/python3.9 -u server.py > server.log 2> server.error

