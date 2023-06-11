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

from config import interface, port, servo_pins, starting_angles, mouse_sensitivity, keyboard_sensitivity, control_mode, limits, mirror_video_axis, mirror_control_axis, axis_movements, long_press_threshold, server_ip_override


current_click = -1
pressed_ms = {"stop": 0, "left": 0, "right": 0, "up": 0, "down": 0}  # The last time when a specific button was unpressed
curr_pressed_arrows = {"up": False, "down": False, "left": False, "right": False}
MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp',
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()


# Servo options
# [vertical, horizontal]
pos = deepcopy(starting_angles)  # Current position of servos
delta = [0, 0]  # Servo delta at each moment in time in range [-1, 1]

pwm = pigpio.pi()

pwm.set_mode(servo_pins[0], pigpio.OUTPUT)
pwm.set_PWM_frequency(servo_pins[0], 50)
pwm.set_servo_pulsewidth(servo_pins[0], pos[0])

pwm.set_mode(servo_pins[1], pigpio.OUTPUT)
pwm.set_PWM_frequency(servo_pins[1], 50)
pwm.set_servo_pulsewidth(servo_pins[1], pos[1])


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
        # if current_ms_time() - pressed_ms["up"] < long_press_threshold:
        #     pos[0] -= big_step[0]

        if not curr_pressed_arrows["down"]:
            delta[0] = 0

def down(pressed):
    if pressed:
        curr_pressed_arrows["down"] = True
        delta[0] = keyboard_sensitivity
    else:
        curr_pressed_arrows["down"] = False
        # if current_ms_time() - pressed_ms["down"] < long_press_threshold:
        #     pos[0] += big_step[0]

        if not curr_pressed_arrows["up"]:
            delta[0] = 0

def left(pressed):
    if pressed:
        curr_pressed_arrows["left"] = True
        delta[1] = -keyboard_sensitivity
    else:
        curr_pressed_arrows["left"] = False
        # if current_ms_time() - pressed_ms["left"] < long_press_threshold:
        #     pos[1] += big_step[1]

        if not curr_pressed_arrows["right"]:
            delta[1] = 0

def right(pressed):
    if pressed:
        curr_pressed_arrows["right"] = True
        delta[1] = keyboard_sensitivity
    else:
        curr_pressed_arrows["right"] = False
        # if current_ms_time() - pressed_ms["right"] < long_press_threshold:
        #     pos[1] -= big_step[1]

        if not curr_pressed_arrows["left"]:
            delta[1] = 0


# Use separate socket for servo controls and socketio channel for streaming only
@sio.on("up")
async def handle_up(sio, pressed):
    if axis_movements[0]:
        if mirror_control_axis[0]:
            down(pressed)
        else:
            up(pressed)

    return web.Response(text="ok")


@sio.on("down")
async def handle_down(sio, pressed):
    if axis_movements[0]:
        if mirror_control_axis[0]:
            up(pressed)
        else:
            down(pressed)

    return web.Response(text="ok")


@sio.on("left")
async def handle_left(sio, pressed):
    if axis_movements[1]:
        if mirror_control_axis[1]:
            right(pressed)
        else:
            left(pressed)

    return web.Response(text="ok")


@sio.on("right")
async def handle_right(sio, pressed):
    if axis_movements[1]:
        if mirror_control_axis[1]:
            left(pressed)
        else:
            right(pressed)

    return web.Response(text="ok")


@sio.on("move")
async def move(sio, dx, dy):
    if mirror_control_axis[0]:
        dx = -dx
    if mirror_control_axis[1]:
        dy = -dy

    if control_mode == "joystick":
        delta[0] = dx * mouse_sensitivity
        delta[1] = dy * mouse_sensitivity
    elif control_mode == "drag":
        pos[0] = min(limits[0][1], max(limits[0][0], pos[0] + dx * mouse_sensitivity))  # Vertical
        pos[1] = min(limits[0][1], max(limits[0][0], pos[1] - dy * mouse_sensitivity))  # Horizontal


@sio.on("stop")
async def stop(sio):
    delta[0] = 0
    delta[1] = 0


@sio.on("reset")
async def reset(sio):
    pos[0] = starting_angles[0]
    pos[1] = starting_angles[1]


@sio.on("set_pos")
async def set_pos(sio, x, y):
    pos[0] = x
    pos[1] = y


async def handle_options_get(request):  # Gives options about both streaming server and control server (from config.py)
    dictionary = {}
    with open("config.py", 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        sp = line.split("=")
        if len(sp) < 2: continue

        key, value = sp[0].strip(), sp[1].split("  #")[0].strip().replace("True", "true").replace("False", "false")
        value = json.loads(value)
        dictionary[key] = value

    return web.json_response(dictionary)


async def handle_restart(request):
    os.execl(sys.executable, sys.executable, *sys.argv)


async def handle_poweroff(request):
    os.system("sudo poweroff")


async def handle_options_set(request):
    global capture, control_mode, camera_index, resolution, encode_param, mouse_sensitivity, keyboard_sensitivity

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
            lines[i] = f"{option} = {repr(value)}\n"

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


    web.run_app(init_app(), host=machine_ip, port=port)

