import cv2
from time import sleep
import base64
import signal

import socketio
import asyncio
from aiohttp import web
import eventlet

from config import ip_address, port, cors_allowed_origins


MAX_BUFFER_SIZE = 50 * 1000 * 1000  # 50 MB

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins=cors_allowed_origins,
                                   maxHttpBufferSize=MAX_BUFFER_SIZE, async_handlers=True)
app = web.Application()
sio.attach(app)

# cv2 Video capture
wCap = cv2.VideoCapture(0)
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

# Servo options
pos = (0, 0)
delta = (0, 0)


# Static files server
async def index(request):
    with open('static/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


app.router.add_static('/static', 'static')
app.router.add_get('/', index)


@sio.on('up')
async def up(sid):
    print("up")

@sio.on('down')
async def down(sid):
    print("down")

@sio.on('left')
async def left(sid):
    print("left")

@sio.on('right')
async def right(sid):
    print("right")


async def send_images():
    while True:
        ret, frame = wCap.read()
        frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        ret, image = cv2.imencode('.jpg', frame, encode_param)
        converted = base64.b64encode(image)
        await sio.emit('image', str(converted)[2:-1])

        await sio.sleep(0.1)

async def init_app():
    sio.start_background_task(send_images)
    return app


if __name__ == "__main__":
    eventlet.monkey_patch()

    web.run_app(init_app(), host=ip_address, port=port)
    wCap.release()
