#!/bin/sh
sudo pigpiod
sleep 10
cd /home/pavtiger/Docs/remote-joystick-control/; /usr/bin/python3.9 server.py

