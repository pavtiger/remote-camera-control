import cv2
import os
import sys
import json
import time
import base64
import subprocess
from copy import deepcopy
from multidict import MultiDict

import socketio
from aiohttp import web
import eventlet

import pigpio

from config import interface, port, servo_pins, starting_angles, camera_index, resolution, step, spill_threshold, control_mode, limits, mirror_video_axis, mirror_control_axis, axis_movements, big_step, long_press_threshold, server_ip_override, video_encoding


last_ms = {"stop": 0, "left": 0, "right": 0, "up": 0, "down": 0}  # The last time when a specific button was unpressed
pressed_ms = {"stop": 0, "left": 0, "right": 0, "up": 0, "down": 0}  # The last time when a specific button was unpressed
MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp',
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()


def list_ports():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    non_working_ports = []
    dev_port = 0
    working_ports = []
    available_ports = []
    while len(non_working_ports) < 6: # if there are more than 5 non working ports stop the testing.
        camera = cv2.VideoCapture(dev_port)
        if not camera.isOpened():
            non_working_ports.append(dev_port)
            print("Port %s is not working." %dev_port)
        else:
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                print("Port %s is working and reads images (%s x %s)" %(dev_port,h,w))
                working_ports.append(dev_port)
            else:
                print("Port %s for camera ( %s x %s) is present but does not reads." %(dev_port,h,w))
                available_ports.append(dev_port)
        dev_port +=1
    return available_ports,working_ports,non_working_ports


# cv2 Video capture
def init_camera(camera_index, resolution):
    capture = cv2.VideoCapture(camera_index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    return capture


system_cameras = list_ports()[1]

capture = init_camera(camera_index, resolution)
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), video_encoding]

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


def up(pressed):
    if pressed == "1" and (current_ms_time() - last_ms["up"]) > spill_threshold:
        delta[0] = -0.5
        pressed_ms["up"] = current_ms_time()
    elif pressed == "0":
        if current_ms_time() - pressed_ms["up"] < long_press_threshold:
            pos[0] -= big_step[0]

        delta[0] = 0
        last_ms["up"] = current_ms_time()

def down(pressed):
    if pressed == "1" and (current_ms_time() - last_ms["down"]) > spill_threshold:
        delta[0] = 0.5
        pressed_ms["down"] = current_ms_time()
    elif pressed == "0":
        if current_ms_time() - pressed_ms["down"] < long_press_threshold:
            pos[0] += big_step[0]

        delta[0] = 0
        last_ms["down"] = current_ms_time()

def left(pressed):
    if pressed == "1" and (current_ms_time() - last_ms["left"]) > spill_threshold:
        delta[1] = -0.5
        pressed_ms["left"] = current_ms_time()
    elif pressed == "0":
        if current_ms_time() - pressed_ms["left"] < long_press_threshold:
            pos[1] += big_step[1]

        delta[1] = 0
        last_ms["left"] = current_ms_time()

def right(pressed):
    if pressed == "1" and (current_ms_time() - last_ms["right"]) > spill_threshold:
        delta[1] = 0.5
        pressed_ms["right"] = current_ms_time()
    elif pressed == "0":
        if current_ms_time() - pressed_ms["right"] < long_press_threshold:
            pos[1] -= big_step[1]

        delta[1] = 0
        last_ms["right"] = current_ms_time()


# Use http for servo controls and socketio channel for streaming only
async def handle_up(request):
    pressed = request.match_info.get('pressed', "none")

    if axis_movements[0]:
        if mirror_control_axis[0]:
            down(pressed)
        else:
            up(pressed)

    return web.Response(text="ok")


async def handle_down(request):
    pressed = request.match_info.get('pressed', "none")

    if axis_movements[0]:
        if mirror_control_axis[0]:
            up(pressed)
        else:
            down(pressed)

    return web.Response(text="ok")


async def handle_left(request):
    pressed = request.match_info.get('pressed', "none")

    if axis_movements[1]:
        if mirror_control_axis[1]:
            right(pressed)
        else:
            left(pressed)

    return web.Response(text="ok")


async def handle_right(request):
    pressed = request.match_info.get('pressed', "none")

    if axis_movements[1]:
        if mirror_control_axis[1]:
            left(pressed)
        else:
            right(pressed)

    return web.Response(text="ok")


async def handle_move(request):
    dx = [0, float(request.match_info.get('dx', "none"))][axis_movements[0]]
    dy = [0, float(request.match_info.get('dy', "none"))][axis_movements[1]]

    if mirror_control_axis[0]:
        dx = -dx
    if mirror_control_axis[1]:
        dy = -dy

    if (current_ms_time() - last_ms["stop"]) > spill_threshold:
        if control_mode == "joystick":
            delta[0] = dx
            delta[1] = dy
        else:
            pos[0] = min(limits[0][1], max(limits[0][0], pos[0] + dx * step[0]))  # Vertical
            pos[1] = min(limits[0][1], max(limits[0][0], pos[1] - dy * step[1]))  # Horizontal


async def handle_stop(request):
    last_ms["stop"] = current_ms_time()
    delta[0] = 0
    delta[1] = 0


async def handle_reset(request):
    pos[0] = starting_angles[0]
    pos[1] = starting_angles[1]


async def handle_options_get(request):
    dictionary = {
        'servo_pins': servo_pins,
        'starting_angles': starting_angles,
        'limits': limits,
        'step': step,
        'big_step': big_step,
        'camera_index': camera_index,
        'resolution': resolution,
        'video_encoding': video_encoding,
        'control_mode': control_mode,
        'mirror_video_axis': mirror_video_axis,
        'mirror_control_axis': mirror_control_axis,
        'axis_movements': axis_movements,
    }

    return web.json_response(dictionary)


async def handle_get_cameras(request):
    return web.json_response(system_cameras)


async def handle_restart(request):
    capture.release()
    os.execl(sys.executable, sys.executable, *sys.argv)


async def handle_poweroff(request):
    os.system("sudo poweroff")


async def handle_options_set(request):
    global capture, control_mode, camera_index, resolution, encode_param

    option = request.match_info.get('option', "none")
    value = request.match_info.get('value', "none")
    value = json.loads(value)

    # Save updated option to config.py
    with open("config.py", 'r') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        sp = line.split("=")
        if len(sp) < 2: continue

        key, val = sp[0].strip(), sp[1].strip()

        if key == option:
            lines[i] = f"{option} = {repr(value)}\n"

    with open("config.py", "w") as file:
        file.writelines(lines)


    # Update on the go
    if option == "camera_index":
        capture.release()
        camera_index = value
        capture = init_camera(camera_index, resolution)

    elif option == "resolution":
        capture.release()
        resolution[0] = value[0]
        resolution[1] = value[1]
        capture = init_camera(camera_index, resolution)

    elif option == "video_encoding":
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), value]

    elif option == "starting_angles":
        pos[0] = value[0]
        pos[1] = value[1]

    elif option == "step":
        step[0] = value[0]
        step[1] = value[1]

    elif option == "control_mode":
        control_mode = value

    elif option == "mirror_video_axis":
        mirror_video_axis[0] = value[0]
        mirror_video_axis[1] = value[1]

    elif option == "mirror_control_axis":
        mirror_control_axis[0] = value[0]
        mirror_control_axis[1] = value[1]

    elif option == "axis_movements":
        axis_movements[0] = value[0]
        axis_movements[1] = value[1]
    
    elif option == "big_step":
        big_step[0] = value[0]
        big_step[1] = value[1]


app.router.add_post('/up_{pressed}', handle_up)
app.router.add_post('/down_{pressed}', handle_down)
app.router.add_post('/left_{pressed}', handle_left)
app.router.add_post('/right_{pressed}', handle_right)

app.router.add_post('/move_{dx}_{dy}', handle_move)
app.router.add_post('/stop', handle_stop)
app.router.add_post('/reset', handle_reset)
app.router.add_get('/available_cameras', handle_get_cameras)

app.router.add_post('/restart', handle_restart)
app.router.add_post('/poweroff', handle_poweroff)

app.router.add_get('/options', handle_options_get)
app.router.add_post('/change-{option}-{value}', handle_options_set)

sio.attach(app)


# Static files server
async def index(request):
    with open('static/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


app.router.add_static('/static', 'static')
app.router.add_get('/', index)


@sio.on("move")
async def move(sio, dx, dy):
    delta[0] = dx
    delta[1] = dy

@sio.on("stop")
async def stop(sio):
    delta[0] = 0
    delta[1] = 0

@sio.on("reset")
async def reset(sio):
    pos[0] = starting_angles[0]
    pos[1] = starting_angles[1]


async def send_images():
    while True:
        grabbed, frame = capture.read()
        if not grabbed:
            break

        for axis in [0, 1]:
            if mirror_video_axis[axis]:
                frame = cv2.flip(frame, axis)

        _, image = cv2.imencode('.jpg', frame, encode_param)
        converted = base64.b64encode(image)
        await sio.emit('image', str(converted)[2:-1])

        await sio.sleep(0.01)


async def move_camera():
    while True:
        pos[0] = min(2500, max(500, pos[0] + delta[0] * step[0]))  # Vertical
        pos[1] = min(2500, max(500, pos[1] - delta[1] * step[1]))  # Horizontal

        pwm.set_servo_pulsewidth(servo_pins[0], pos[0])
        pwm.set_servo_pulsewidth(servo_pins[1], pos[1])

        await sio.sleep(0.01)


async def init_app():
    sio.start_background_task(send_images)
    sio.start_background_task(move_camera)
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
                    f.write(f'var server_address = "http://{machine_ip}:{port}";')
                else:
                    f.write(f'var server_address = "{server_ip_override}";')

            print("Network has been connected, starting web server")
            break

        time.sleep(3)


    web.run_app(init_app(), host=machine_ip, port=port)
    capture.release()

