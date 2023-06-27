import os
import sys
import json
import time
import subprocess
from copy import deepcopy
from multidict import MultiDict

import socketio
from aiohttp import web
import aiohttp_cors
import eventlet

import pigpio
import RPi.GPIO as GPIO

from config import interface, port, servo_pins, starting_angles, mouse_sensitivity, keyboard_sensitivity, control_mode, limits, mirror_control_axis, axis_movements, server_ip_override


current_click = -1
lazer_on_ms = None
pressed_ms = {"stop": 0, "left": 0, "right": 0, "up": 0, "down": 0}  # The last time when a specific button was unpressed
curr_pressed_arrows = {"up": False, "down": False, "left": False, "right": False}
MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB
video_streamer = None

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp',
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()


# Servo options
# [vertical, horizontal]
pos = deepcopy(starting_angles)  # Current position of servos
delta = [0, 0]  # Servo delta at each moment in time in range [-1, 1]

pwm = pigpio.pi()

# Servos
pwm.set_mode(servo_pins[0], pigpio.OUTPUT)
pwm.set_PWM_frequency(servo_pins[0], 50)
pwm.set_servo_pulsewidth(servo_pins[0], pos[0])

pwm.set_mode(servo_pins[1], pigpio.OUTPUT)
pwm.set_PWM_frequency(servo_pins[1], 50)
pwm.set_servo_pulsewidth(servo_pins[1], pos[1])

# LED/lazer
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.LOW)


def current_ms_time():
    return round(time.time() * 1000)


def pressed_cnt():
    return curr_pressed_arrows["up"] + curr_pressed_arrows["down"] + curr_pressed_arrows["left"] + curr_pressed_arrows["right"]


def up(pressed):
    if pressed:
        curr_pressed_arrows["up"] = True
        delta[0] = -keyboard_sensitivity
    else:
        curr_pressed_arrows["up"] = False

        if not curr_pressed_arrows["down"]:
            delta[0] = 0

def down(pressed):
    if pressed:
        curr_pressed_arrows["down"] = True
        delta[0] = keyboard_sensitivity
    else:
        curr_pressed_arrows["down"] = False

        if not curr_pressed_arrows["up"]:
            delta[0] = 0

def left(pressed):
    if pressed:
        curr_pressed_arrows["left"] = True
        delta[1] = -keyboard_sensitivity
    else:
        curr_pressed_arrows["left"] = False

        if not curr_pressed_arrows["right"]:
            delta[1] = 0

def right(pressed):
    if pressed:
        curr_pressed_arrows["right"] = True
        delta[1] = keyboard_sensitivity
    else:
        curr_pressed_arrows["right"] = False

        if not curr_pressed_arrows["left"]:
            delta[1] = 0


# Use separate socket for servo controls and socketio channel for streaming only
@sio.on("up")
async def handle_up(sid, pressed):
    if axis_movements[0]:
        if mirror_control_axis[0]:
            down(pressed)
        else:
            up(pressed)

    return web.Response(text="ok")


@sio.on("down")
async def handle_down(sid, pressed):
    if axis_movements[0]:
        if mirror_control_axis[0]:
            up(pressed)
        else:
            down(pressed)

    return web.Response(text="ok")


@sio.on("left")
async def handle_left(sid, pressed):
    if axis_movements[1]:
        if mirror_control_axis[1]:
            right(pressed)
        else:
            left(pressed)

    return web.Response(text="ok")


@sio.on("right")
async def handle_right(sid, pressed):
    if axis_movements[1]:
        if mirror_control_axis[1]:
            left(pressed)
        else:
            right(pressed)

    return web.Response(text="ok")


@sio.on("move")
async def move(sid, dx, dy):
    if mirror_control_axis[0]:
        dx = -dx
    if mirror_control_axis[1]:
        dy = -dy

    if not axis_movements[0]:
        dx = 0
    if not axis_movements[1]:
        dy = 0

    if control_mode == "joystick":
        delta[0] = dx * mouse_sensitivity
        delta[1] = dy * mouse_sensitivity
    elif control_mode == "drag":
        pos[0] = min(limits[0][1], max(limits[0][0], pos[0] + dx * mouse_sensitivity))  # Vertical
        pos[1] = min(limits[0][1], max(limits[0][0], pos[1] - dy * mouse_sensitivity))  # Horizontal


@sio.on("stop")
async def stop(sid):
    delta[0] = 0
    delta[1] = 0


@sio.on("reset")
async def reset(sid):
    pos[0] = starting_angles[0]
    pos[1] = starting_angles[1]


@sio.on("set_pos")
async def set_pos(sid, x, y):
    pos[0] = x
    pos[1] = y


@sio.on("set_lazer")
async def set_lazer(sid, state):
    global lazer_on_ms

    if state:
        lazer_on_ms = current_ms_time()
        GPIO.output(18, GPIO.HIGH)
    else:
        lazer_on_ms = None
        GPIO.output(18, GPIO.LOW)


async def handle_options_get(request):  # Gives options about both streaming server and control server (from config.py)
    dictionary = {}
    with open("config.py", 'r') as file:
        lines = file.readlines()

    for line in lines:
        sp = line.split("=")
        if len(sp) < 2: continue

        key, value = sp[0].strip(), sp[1].split("  #")[0].strip().replace("True", "true").replace("False", "false").replace("'", '"')
        value = json.loads(value)
        dictionary[key] = value

    return web.json_response(dictionary)


async def handle_restart(request):
    video_streamer.kill()
    os.execl(sys.executable, sys.executable, *sys.argv)


async def handle_poweroff(request):
    os.system("sudo poweroff")


async def handle_options_set(request):
    global control_mode, mouse_sensitivity, keyboard_sensitivity, pwm

    option = request.match_info.get('option', "none")
    value = request.match_info.get('value', "none")
    value = json.loads(value)

    # Save updated option to config.py
    with open("config.py", 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        sp = line.split("=")
        if len(sp) < 2: continue

        key = sp[0].strip()

        if key == option:
            new_val = repr(value).replace("'", '"')
            lines[i] = f"{option} = {new_val}\n"

    with open("config.py", "w") as file:
        file.writelines(lines)


    # Update on the go
    if option == "starting_angles":
        pos[0] = value[0]
        pos[1] = value[1]

    elif option == "mouse_sensitivity":
        mouse_sensitivity = value

    elif option == "keyboard_sensitivity":
        keyboard_sensitivity = value

    elif option == "control_mode":
        control_mode = value

    elif option == "mirror_control_axis":
        mirror_control_axis[0] = value[0]
        mirror_control_axis[1] = value[1]

    elif option == "axis_movements":
        axis_movements[0] = value[0]
        axis_movements[1] = value[1]

    elif option == "servo_pins":
        servo_pins[0] = value[0]
        servo_pins[1] = value[1]

        pwm.stop()
        pwm = pigpio.pi()

        pwm.set_mode(servo_pins[0], pigpio.OUTPUT)
        pwm.set_PWM_frequency(servo_pins[0], 50)
        pwm.set_servo_pulsewidth(servo_pins[0], pos[0])

        pwm.set_mode(servo_pins[1], pigpio.OUTPUT)
        pwm.set_PWM_frequency(servo_pins[1], 50)
        pwm.set_servo_pulsewidth(servo_pins[1], pos[1])


# @asyncio.coroutine
async def handler(request):
    return web.Response(
        text="Hello!",
        headers={
            "X-Custom-Server-Header": "Custom data",
        })


# Handle interactions with options
app.router.add_post('/restart', handle_restart)
app.router.add_post('/poweroff', handle_poweroff)

app.router.add_get('/options', handle_options_get)
app.router.add_post('/change-{option}-{value}', handle_options_set)


cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*"
    )
})

for route in list(app.router.routes()):
    cors.add(route)

sio.attach(app)


# Static files server
async def index(request):
    with open('static/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


app.router.add_static('/static', 'static')  # Route static files
app.router.add_get('/', index)  # Index page


async def move_camera():
    while True:
        pos[0] = min(2500, max(500, pos[0] + delta[0]))  # Vertical
        pos[1] = min(2500, max(500, pos[1] - delta[1]))  # Horizontal

        pwm.set_servo_pulsewidth(servo_pins[0], pos[0])
        pwm.set_servo_pulsewidth(servo_pins[1], pos[1])

        await sio.sleep(0.01)


async def send_pos():
    while True:
        await sio.emit("update_pos", pos)
        if lazer_on_ms is not None and (current_ms_time() - lazer_on_ms) > 15000:  # Turn off LED/lazer fter 15 seconds
            GPIO.output(18, GPIO.LOW)
            await sio.emit("turn_off_lazer")

        await sio.sleep(0.5)


async def init_app():
    sio.start_background_task(move_camera)
    sio.start_background_task(send_pos)
    return app


if __name__ == "__main__":
    eventlet.monkey_patch()

    # Clear ip.js
    with open("static/ip.js", "w") as f:
        f.write(f"network is not yet connected on interface {interface}")

    print(f"Waiting for network interface {interface}")
    while True:  # Repeat until network is connected
        machine_ip = subprocess.check_output(f"ip -f inet addr show {interface} | awk '/inet / {{print $2}}'", shell=True).decode("utf-8")[:-1]
        machine_ip = machine_ip.split('/')[0]

        if machine_ip != "":
            with open("static/ip.js", "w") as f:
                if server_ip_override == "":
                    f.writelines([f'var control_address = "http://{machine_ip}:{port}";\n',
                        f'var video_address = "http://{machine_ip}:{port + 1}";'])
                else:
                    f.write(f'var server_address = "{server_ip_override}";')

            print("Network has been connected, starting web server")
            break

        time.sleep(3)

    video_streamer = subprocess.Popen(['/usr/bin/python3.9', 'stream.py', '--ip', machine_ip, '--port', str(port + 1)])
    web.run_app(init_app(), host=machine_ip, port=port)

