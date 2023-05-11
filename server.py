import cv2
import time
import base64
import signal
import subprocess
from copy import deepcopy

import socketio
import asyncio
from aiohttp import web
import eventlet

import pigpio

from config import interface, port, servo_pins, starting_angles, camera_index, resolution, step


MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB


# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp',
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()
sio.attach(app)

# cv2 Video capture
capture = cv2.VideoCapture(camera_index)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

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


# Static files server
async def index(request):
    with open('static/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


app.router.add_static('/static', 'static')
app.router.add_get('/', index)


@sio.on('up')
async def up(sid, pressed):
    if pressed:
        delta[0] = -0.5
    else:
        delta[0] = 0

@sio.on('down')
async def down(sid, pressed):
    if pressed:
        delta[0] = 0.5
    else:
        delta[0] = 0

@sio.on('left')
async def left(sid, pressed):
    if pressed:
        delta[1] = -0.5
    else:
        delta[1] = 0

@sio.on('right')
async def right(sid, pressed):
    if pressed:
        delta[1] = 0.5
    else:
        delta[1] = 0


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

        ret, image = cv2.imencode('.jpg', frame, encode_param)
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
                f.write(f'var server_address = "http://{machine_ip}:{port}";')
            print("Network has been connected, starting web server")
            break

        time.sleep(3)

    web.run_app(init_app(), host=machine_ip, port=port)
    capture.release()

