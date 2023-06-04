import cv2
import argparse
import base64
import json

import uvicorn
import socketio
from aiohttp import web
import aiohttp_cors
import eventlet

from config import camera_index, resolution, video_encoding, mirror_video_axis, cors_allowed_origins


ap = argparse.ArgumentParser()
ap.add_argument("--ip", required=True, help="ip", default="")
ap.add_argument("--port", required=True, help="port", default="")
args = vars(ap.parse_args())


# Create a Socket.IO server
MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins=cors_allowed_origins,
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()

# Static files server
async def index(request):
    with open('static/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


app.router.add_static('/static', 'static')
app.router.add_get('/', index)


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
        dev_port += 1
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


async def handle_get_cameras(request):
    return web.json_response(system_cameras)


@sio.on("options")
async def handle_options_set(request, option, value):
    global capture, control_mode, camera_index, resolution, encode_param
    # value = json.loads(value)

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
        value = json.loads(value)
        resolution[0] = value[0]
        resolution[1] = value[1]
        capture = init_camera(camera_index, resolution)

    elif option == "video_encoding":
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), value]

    elif option == "mirror_video_axis":
        mirror_video_axis[0] = value[0]
        mirror_video_axis[1] = value[1]


# resource = cors.add(app.router.add_resource("/available_cameras"))
# route = cors.add(
#     resource.add_route("GET", handler), {
#         "http://192.168.1.150:9002": aiohttp_cors.ResourceOptions(
#             allow_credentials=True,
#             expose_headers=("X-Custom-Server-Header",),
#             allow_headers=("X-Requested-With", "Content-Type"),
#             max_age=3600,
#         )
#     }

app.router.add_get('/available_cameras', handle_get_cameras)
# app.router.add_post('/change-{option}-{value}', handle_options_set)

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


async def init_app():
    sio.start_background_task(send_images)
    return app


if __name__ == "__main__":
    eventlet.monkey_patch()
    web.run_app(init_app(), host="192.168.1.159", port=9003)
    capture.release()

